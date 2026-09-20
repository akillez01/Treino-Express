-- ============================================================================
-- Treino Express · Schema PostgreSQL 16
-- SaaS multi-tenant para academias: treino, anúncios na TV e jukebox.
--
-- Aplicar com:
--   psql postgresql://treino:treino@localhost:5432/treino_express -f 04-banco-de-dados.sql
--
-- Toda tabela de domínio carrega academia_id e tem Row Level Security amarrada
-- ao tenant da sessão. O backend deve executar, a cada requisição:
--   SET LOCAL app.academia_id = '<uuid da academia do token>';
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Tipos
-- ---------------------------------------------------------------------------
CREATE TYPE plano_aluno        AS ENUM ('mensal', 'trimestral', 'anual');
CREATE TYPE situacao_pagamento AS ENUM ('em_dia', 'pendente', 'atrasado');
CREATE TYPE foco_muscular      AS ENUM ('cardio', 'superiores', 'pernas', 'fullbody');
CREATE TYPE status_campanha    AS ENUM ('rascunho', 'ativa', 'pausada', 'encerrada');
CREATE TYPE status_tela        AS ENUM ('online', 'pausada', 'offline');
CREATE TYPE origem_lancamento  AS ENUM ('mensalidade', 'anuncio', 'jukebox');
CREATE TYPE status_lancamento  AS ENUM ('liquidado', 'a_receber', 'recusado');
CREATE TYPE status_repasse     AS ENUM ('pendente', 'em_transito', 'pago', 'falhou');

-- ---------------------------------------------------------------------------
-- Tenants
-- ---------------------------------------------------------------------------
CREATE TABLE academias (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                TEXT        NOT NULL,
    slug                TEXT        NOT NULL UNIQUE,
    unidade             TEXT,
    cidade              TEXT,
    bairro              TEXT,
    cnpj                TEXT        UNIQUE,
    stripe_account_id   TEXT        UNIQUE,          -- conta conectada (Express)
    charges_enabled     BOOLEAN     NOT NULL DEFAULT FALSE,
    payouts_enabled     BOOLEAN     NOT NULL DEFAULT FALSE,
    percentual_repasse  NUMERIC(5,2) NOT NULL DEFAULT 60.00,
    ativa               BOOLEAN     NOT NULL DEFAULT TRUE,
    criada_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN academias.percentual_repasse IS
    'Fatia da verba do anunciante repassada a esta academia. Padrão 60%.';

-- ---------------------------------------------------------------------------
-- Anunciantes e campanhas
-- ---------------------------------------------------------------------------
CREATE TABLE anunciantes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                TEXT        NOT NULL,
    categoria           TEXT,                        -- 'Suplementos', 'Alimentação', ...
    cnpj                TEXT        UNIQUE,
    email_contato       TEXT        NOT NULL,
    telefone            TEXT,
    distancia_metros    INTEGER,                     -- proximidade usada no criativo da TV
    stripe_customer_id  TEXT        UNIQUE,
    saldo_centavos      BIGINT      NOT NULL DEFAULT 0 CHECK (saldo_centavos >= 0),
    ativo               BOOLEAN     NOT NULL DEFAULT TRUE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE campanhas_ads (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anunciante_id       UUID        NOT NULL REFERENCES anunciantes(id) ON DELETE CASCADE,
    academia_id         UUID        NOT NULL REFERENCES academias(id)   ON DELETE CASCADE,
    nome                TEXT        NOT NULL,
    -- criativo exibido na TV
    desconto_rotulo     TEXT        NOT NULL,        -- '15%', '1ª', '20%'
    manchete            TEXT        NOT NULL,        -- 'OFF em toda a linha de whey'
    corpo               TEXT        NOT NULL,
    cupom               TEXT        NOT NULL,
    criativo_url        TEXT,                        -- imagem opcional no object storage
    -- veiculação
    status              status_campanha NOT NULL DEFAULT 'rascunho',
    inicio              DATE        NOT NULL,
    fim                 DATE,
    hora_inicio         TIME        NOT NULL DEFAULT '06:00',
    hora_fim            TIME        NOT NULL DEFAULT '22:00',
    duracao_exibicao_s  SMALLINT    NOT NULL DEFAULT 24 CHECK (duracao_exibicao_s BETWEEN 5 AND 120),
    -- verba
    orcamento_centavos      BIGINT  NOT NULL CHECK (orcamento_centavos > 0),
    gasto_centavos          BIGINT  NOT NULL DEFAULT 0 CHECK (gasto_centavos >= 0),
    cpm_centavos            INTEGER NOT NULL DEFAULT 0,
    limite_diario_centavos  BIGINT,
    criada_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (fim IS NULL OR fim >= inicio),
    CHECK (hora_fim > hora_inicio)
);

CREATE INDEX idx_campanhas_academia_status ON campanhas_ads (academia_id, status);
CREATE INDEX idx_campanhas_anunciante      ON campanhas_ads (anunciante_id);
CREATE INDEX idx_campanhas_janela          ON campanhas_ads (academia_id, inicio, fim)
    WHERE status = 'ativa';

-- ---------------------------------------------------------------------------
-- Catálogo de exercícios
-- ---------------------------------------------------------------------------
CREATE TABLE exercicios (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        REFERENCES academias(id) ON DELETE CASCADE,
    nome                TEXT        NOT NULL,        -- 'Cadeira Extensora'
    foco                foco_muscular NOT NULL,
    grupo_muscular      TEXT,                        -- 'Quadríceps'
    series_padrao       TEXT        NOT NULL,        -- '3x12', '12 min', '4x30s'
    carga_sugerida      TEXT,                        -- 'Carga 25 kg'
    descanso_segundos   SMALLINT    NOT NULL DEFAULT 60 CHECK (descanso_segundos BETWEEN 15 AND 300),
    duracao_estimada_s  SMALLINT    NOT NULL DEFAULT 180,
    equipamento         TEXT,
    video_url           TEXT,
    ordem_preferencial  SMALLINT    NOT NULL DEFAULT 100,
    ativo               BOOLEAN     NOT NULL DEFAULT TRUE
);

COMMENT ON COLUMN exercicios.academia_id IS
    'NULL = exercício do catálogo global da plataforma, visível a todas as academias.';

CREATE INDEX idx_exercicios_foco ON exercicios (foco, ativo);
CREATE INDEX idx_exercicios_academia ON exercicios (academia_id) WHERE academia_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Alunos, treinos e check-ins
-- ---------------------------------------------------------------------------
CREATE TABLE alunos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    nome                TEXT        NOT NULL,
    email               TEXT        NOT NULL,
    telefone            TEXT,
    plano               plano_aluno NOT NULL DEFAULT 'mensal',
    mensalidade_centavos INTEGER    NOT NULL,
    situacao            situacao_pagamento NOT NULL DEFAULT 'em_dia',
    matriculado_em      DATE        NOT NULL DEFAULT CURRENT_DATE,
    cancelado_em        DATE,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (academia_id, email)
);

CREATE INDEX idx_alunos_academia_situacao ON alunos (academia_id, situacao);

CREATE TABLE treinos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    aluno_id            UUID        NOT NULL REFERENCES alunos(id)    ON DELETE CASCADE,
    minutos_disponiveis SMALLINT    NOT NULL CHECK (minutos_disponiveis BETWEEN 15 AND 60),
    foco                foco_muscular NOT NULL,
    iniciado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em        TIMESTAMPTZ
);

CREATE INDEX idx_treinos_aluno ON treinos (aluno_id, iniciado_em DESC);

CREATE TABLE treino_exercicios (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    treino_id           UUID        NOT NULL REFERENCES treinos(id)    ON DELETE CASCADE,
    exercicio_id        UUID        NOT NULL REFERENCES exercicios(id) ON DELETE RESTRICT,
    ordem               SMALLINT    NOT NULL,
    series              TEXT        NOT NULL,
    carga               TEXT,
    concluido_em        TIMESTAMPTZ,
    UNIQUE (treino_id, ordem)
);

CREATE TABLE descansos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    treino_exercicio_id UUID        NOT NULL REFERENCES treino_exercicios(id) ON DELETE CASCADE,
    campanha_id         UUID        REFERENCES campanhas_ads(id) ON DELETE SET NULL,
    duracao_segundos    SMALLINT    NOT NULL,
    iniciado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
    pulado              BOOLEAN     NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE descansos IS
    'Cada descanso é a janela em que um anúncio pode ser exibido. Liga treino, aluno e campanha.';

CREATE TABLE check_ins (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    aluno_id            UUID        NOT NULL REFERENCES alunos(id)    ON DELETE CASCADE,
    entrada_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    saida_em            TIMESTAMPTZ
);

CREATE INDEX idx_checkins_academia_data ON check_ins (academia_id, entrada_em DESC);
CREATE INDEX idx_checkins_aluno         ON check_ins (aluno_id, entrada_em DESC);

-- ---------------------------------------------------------------------------
-- Telas (TVs)
-- ---------------------------------------------------------------------------
CREATE TABLE telas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    sala                TEXT        NOT NULL,        -- 'Sala de musculação'
    resolucao           TEXT        NOT NULL DEFAULT '1920x1080',
    codigo_pareamento   TEXT        UNIQUE,          -- '4K7-92B', apagado após parear
    pareada_em          TIMESTAMPTZ,
    status              status_tela NOT NULL DEFAULT 'offline',
    ultimo_heartbeat    TIMESTAMPTZ,
    criada_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_telas_academia ON telas (academia_id, status);

-- ---------------------------------------------------------------------------
-- Métricas de anúncio
-- ---------------------------------------------------------------------------
CREATE TABLE impressoes (
    id                  BIGSERIAL PRIMARY KEY,
    academia_id         UUID        NOT NULL REFERENCES academias(id)     ON DELETE CASCADE,
    campanha_id         UUID        NOT NULL REFERENCES campanhas_ads(id) ON DELETE CASCADE,
    tela_id             UUID        NOT NULL REFERENCES telas(id)         ON DELETE CASCADE,
    descanso_id         UUID        REFERENCES descansos(id) ON DELETE SET NULL,
    nonce               TEXT        NOT NULL,        -- vai no QR, amarra o scan à exibição
    custo_centavos      INTEGER     NOT NULL DEFAULT 0,
    exibida_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (campanha_id, nonce)
);

CREATE INDEX idx_impressoes_campanha_data ON impressoes (campanha_id, exibida_em DESC);
CREATE INDEX idx_impressoes_academia_data ON impressoes (academia_id, exibida_em DESC);

CREATE TABLE scans (
    id                  BIGSERIAL PRIMARY KEY,
    academia_id         UUID        NOT NULL REFERENCES academias(id)  ON DELETE CASCADE,
    impressao_id        BIGINT      NOT NULL REFERENCES impressoes(id) ON DELETE CASCADE,
    aluno_id            UUID        REFERENCES alunos(id) ON DELETE SET NULL,
    escaneado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resgatado_em        TIMESTAMPTZ,                 -- preenchido quando o cupom é usado na loja
    valor_compra_centavos INTEGER
);

CREATE INDEX idx_scans_impressao ON scans (impressao_id);
CREATE INDEX idx_scans_academia_data ON scans (academia_id, escaneado_em DESC);

-- ---------------------------------------------------------------------------
-- Jukebox
-- ---------------------------------------------------------------------------
CREATE TABLE faixas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo              TEXT        NOT NULL,
    artista             TEXT        NOT NULL,
    duracao_segundos    SMALLINT    NOT NULL,
    capa_url            TEXT,
    provedor            TEXT,                        -- 'spotify', 'local'
    provedor_id         TEXT,
    liberada            BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE jukebox_pedidos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    faixa_id            UUID        NOT NULL REFERENCES faixas(id)    ON DELETE CASCADE,
    aluno_id            UUID        NOT NULL REFERENCES alunos(id)    ON DELETE CASCADE,
    pedido_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    tocado_em           TIMESTAMPTZ,
    valor_centavos      INTEGER     NOT NULL DEFAULT 0   -- pedido avulso pago
);

CREATE INDEX idx_jukebox_fila ON jukebox_pedidos (academia_id, pedido_em)
    WHERE tocado_em IS NULL;

-- ---------------------------------------------------------------------------
-- Financeiro
-- ---------------------------------------------------------------------------
CREATE TABLE lancamentos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
    origem              origem_lancamento NOT NULL,
    descricao           TEXT        NOT NULL,
    valor_centavos      BIGINT      NOT NULL,
    status              status_lancamento NOT NULL DEFAULT 'a_receber',
    competencia         DATE        NOT NULL,        -- primeiro dia do mês de referência
    aluno_id            UUID        REFERENCES alunos(id)        ON DELETE SET NULL,
    campanha_id         UUID        REFERENCES campanhas_ads(id) ON DELETE SET NULL,
    stripe_payment_intent_id TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    liquidado_em        TIMESTAMPTZ
);

CREATE INDEX idx_lancamentos_academia_comp ON lancamentos (academia_id, competencia DESC);

CREATE TABLE repasses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    academia_id         UUID        NOT NULL REFERENCES academias(id)  ON DELETE CASCADE,
    anunciante_id       UUID        NOT NULL REFERENCES anunciantes(id) ON DELETE CASCADE,
    campanha_id         UUID        REFERENCES campanhas_ads(id) ON DELETE SET NULL,
    bruto_centavos      BIGINT      NOT NULL CHECK (bruto_centavos > 0),
    taxa_centavos       BIGINT      NOT NULL CHECK (taxa_centavos >= 0),
    liquido_centavos    BIGINT      NOT NULL CHECK (liquido_centavos >= 0),
    status              status_repasse NOT NULL DEFAULT 'pendente',
    stripe_transfer_id  TEXT        UNIQUE,
    competencia         DATE        NOT NULL,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    pago_em             TIMESTAMPTZ,
    CHECK (bruto_centavos = taxa_centavos + liquido_centavos)
);

COMMENT ON CONSTRAINT repasses_check ON repasses IS
    'Garante que o split fecha em centavos: nada de arredondamento perdido.';

CREATE INDEX idx_repasses_academia_comp ON repasses (academia_id, competencia DESC);

CREATE TABLE creditos_anunciante (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anunciante_id       UUID        NOT NULL REFERENCES anunciantes(id) ON DELETE CASCADE,
    valor_centavos      BIGINT      NOT NULL,        -- positivo = recarga, negativo = consumo
    descricao           TEXT        NOT NULL,
    stripe_payment_intent_id TEXT,
    nota_fiscal         TEXT,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_creditos_anunciante ON creditos_anunciante (anunciante_id, criado_em DESC);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- O backend define o tenant da sessão antes de qualquer query:
--   SET LOCAL app.academia_id = '<uuid>';
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION tenant_atual() RETURNS UUID
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.academia_id', TRUE), '')::UUID;
$$;

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'campanhas_ads', 'alunos', 'treinos', 'descansos', 'check_ins',
        'telas', 'impressoes', 'scans', 'jukebox_pedidos', 'lancamentos', 'repasses'
    ] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %I
                USING (academia_id = tenant_atual())
                WITH CHECK (academia_id = tenant_atual())
        $f$, t);
    END LOOP;
END $$;

-- Exercícios: catálogo global (academia_id NULL) visível a todos os tenants.
ALTER TABLE exercicios ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercicios FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_ou_global ON exercicios
    USING (academia_id IS NULL OR academia_id = tenant_atual())
    WITH CHECK (academia_id = tenant_atual());

-- treino_exercicios herda o tenant via treinos.
ALTER TABLE treino_exercicios ENABLE ROW LEVEL SECURITY;
ALTER TABLE treino_exercicios FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_via_treino ON treino_exercicios
    USING (EXISTS (
        SELECT 1 FROM treinos t
        WHERE t.id = treino_exercicios.treino_id
          AND t.academia_id = tenant_atual()
    ));

-- ---------------------------------------------------------------------------
-- Views de apoio aos painéis
-- ---------------------------------------------------------------------------
CREATE VIEW vw_desempenho_campanha AS
SELECT
    c.id                                        AS campanha_id,
    c.academia_id,
    c.nome,
    COUNT(DISTINCT i.id)                        AS impressoes,
    COUNT(DISTINCT s.id)                        AS scans,
    COUNT(DISTINCT s.id) FILTER (WHERE s.resgatado_em IS NOT NULL) AS resgates,
    COALESCE(SUM(i.custo_centavos), 0)          AS gasto_centavos
FROM campanhas_ads c
LEFT JOIN impressoes i ON i.campanha_id = c.id
LEFT JOIN scans      s ON s.impressao_id = i.id
GROUP BY c.id, c.academia_id, c.nome;

CREATE VIEW vw_receita_mensal AS
SELECT
    academia_id,
    competencia,
    origem,
    SUM(valor_centavos) FILTER (WHERE status = 'liquidado') AS liquidado_centavos,
    SUM(valor_centavos) FILTER (WHERE status = 'a_receber') AS a_receber_centavos
FROM lancamentos
GROUP BY academia_id, competencia, origem;

-- ---------------------------------------------------------------------------
-- Patch pós-handoff (docs/07-catalogo-exercicios.md)
--
-- O enum original só cobria 4 grupos; os protótipos e o catálogo de 29
-- ilustrações usam 6. Ampliamos aqui, na própria baseline, para que o schema
-- aplicado já nasça consistente com o design. Seguro executar dentro desta
-- transação (Postgres 16): a restrição de ALTER TYPE ... ADD VALUE é só não
-- poder *usar* o valor novo na mesma transação em que foi adicionado — nada
-- aqui insere linhas, então não há conflito (o seed roda depois, em outra
-- sessão).
-- ---------------------------------------------------------------------------
ALTER TYPE foco_muscular ADD VALUE 'peito_triceps';
ALTER TYPE foco_muscular ADD VALUE 'costas_biceps';
ALTER TYPE foco_muscular ADD VALUE 'ombros';
ALTER TYPE foco_muscular ADD VALUE 'bracos';

-- Ilustração do exercício, servida do object storage (`exercicios/{slug}.png`).
-- video_url já existia no schema original; imagem_url é o companheiro estático.
ALTER TABLE exercicios ADD COLUMN imagem_url TEXT;

-- ---------------------------------------------------------------------------
-- Role de aplicação (não-superusuário)
--
-- O usuário 'treino' do docker-compose é o superusuário de bootstrap do
-- Postgres — superusuário SEMPRE ignora Row Level Security, mesmo com
-- FORCE ROW LEVEL SECURITY. Se a API se conectasse como 'treino', todo o
-- isolamento multi-tenant desenhado acima seria decorativo. Migrations
-- continuam rodando como 'treino' (precisa de privilégio pra ALTER TYPE,
-- CREATE POLICY etc.); a API roda como 'treino_app', que é uma role comum e
-- portanto está sujeita às policies como qualquer usuário não-dono da tabela.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'treino_app') THEN
        CREATE ROLE treino_app LOGIN PASSWORD 'treino_app';
    END IF;
END
$$;

DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO treino_app', current_database());
END
$$;

GRANT USAGE ON SCHEMA public TO treino_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO treino_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO treino_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO treino_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO treino_app;
