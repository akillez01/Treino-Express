"""Popula dados de demonstração para os painéis (academia e anunciante).

Roda como superusuário (`migrations_database_url`): insere em várias academias
e anunciantes de uma vez, o que a role de runtime (sujeita a RLS) não faz.
Idempotente: apaga os dados demo (IDs fixos abaixo) e recria.

Uso:
    PYTHONPATH=. uv run python scripts/seed_demo.py
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

IRON = "11111111-1111-1111-1111-111111111111"
POWER = "33333333-3333-3333-3333-333333333333"
STUDIO = "66666666-6666-6666-6666-666666666666"
ALUNO_DEMO = "22222222-2222-2222-2222-222222222222"
NUTRI = "55555555-5555-5555-5555-555555555555"
ACAI = "77777777-7777-7777-7777-777777777777"
FISIO = "88888888-8888-8888-8888-888888888888"
IRONWEAR = "99999999-9999-9999-9999-999999999999"

ACADEMIAS = (IRON, POWER, STUDIO)
ANUNCIANTES = (NUTRI, ACAI, FISIO, IRONWEAR)


def ids(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


# Ordem importa: apaga filhos antes dos pais.
LIMPAR = [
    f"DELETE FROM scans WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM impressoes WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM repasses WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM descansos WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM campanhas_ads WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM creditos_anunciante WHERE anunciante_id IN ({ids(ANUNCIANTES)})",
    f"DELETE FROM jukebox_pedidos WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM lancamentos WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM check_ins WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM telas WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM alunos WHERE academia_id IN ({ids(ACADEMIAS)})",
    f"DELETE FROM anunciantes WHERE id IN ({ids(ANUNCIANTES)})",
    "DELETE FROM faixas WHERE provedor = 'demo'",
]

SEED = [
    "SELECT setseed(0.42)",
    f"""
    INSERT INTO academias (id, nome, slug, unidade, cidade, bairro) VALUES
      ('{IRON}', 'Iron Factory', 'iron-factory', 'Unidade Vila Prudente', 'São Paulo', 'Vila Prudente'),
      ('{POWER}', 'Power House', 'power-house', 'Unidade Mooca', 'São Paulo', 'Mooca'),
      ('{STUDIO}', 'Studio Alta', 'studio-alta', 'Unidade Tatuapé', 'São Paulo', 'Tatuapé')
    ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, unidade = EXCLUDED.unidade,
      cidade = EXCLUDED.cidade, bairro = EXCLUDED.bairro
    """,
    f"""
    INSERT INTO anunciantes (id, nome, categoria, email_contato, distancia_metros, saldo_centavos) VALUES
      ('{NUTRI}', 'Nutri Prime Suplementos', 'Suplementos', 'contato@nutriprime.example', 300, 342000),
      ('{ACAI}', 'Açaí do Ponto', 'Alimentação', 'contato@acaidoponto.example', 80, 90000),
      ('{FISIO}', 'Fisio Movimento', 'Saúde', 'contato@fisiomov.example', 450, 60000),
      ('{IRONWEAR}', 'Loja Iron Wear', 'Vestuário esportivo', 'contato@ironwear.example', 200, 110000)
    """,
    # --- alunos: 10 nomeados (o primeiro é o aluno demo) + 110 gerados
    f"""
    INSERT INTO alunos (id, academia_id, nome, email, plano, mensalidade_centavos, situacao, matriculado_em)
    SELECT v.id::uuid, '{IRON}', v.nome, v.email, v.plano::plano_aluno, v.fee,
           v.pay::situacao_pagamento, v.desde::date
    FROM (VALUES
      ('{ALUNO_DEMO}', 'Marina Rodrigues', 'marina.r@email.com', 'anual', 12990, 'em_dia', '2024-03-10'),
      (gen_random_uuid()::text, 'Diego Santana', 'diego.s@email.com', 'mensal', 15990, 'em_dia', '2026-01-12'),
      (gen_random_uuid()::text, 'Camila Teixeira', 'camila.t@email.com', 'trimestral', 13990, 'atrasado', '2025-08-05'),
      (gen_random_uuid()::text, 'Rafael Lima', 'rafa.lima@email.com', 'mensal', 15990, 'em_dia', '2026-05-20'),
      (gen_random_uuid()::text, 'Júlia Prado', 'julia.p@email.com', 'anual', 12990, 'pendente', '2023-02-14'),
      (gen_random_uuid()::text, 'Lucas Moraes', 'lucas.m@email.com', 'mensal', 15990, 'em_dia', '2026-07-01'),
      (gen_random_uuid()::text, 'Beatriz Alencar', 'bia.alencar@email.com', 'trimestral', 13990, 'em_dia', '2025-09-18'),
      (gen_random_uuid()::text, 'Thiago Nunes', 'thiago.n@email.com', 'mensal', 15990, 'atrasado', '2026-04-03'),
      (gen_random_uuid()::text, 'Renata Vasques', 'renata.v@email.com', 'anual', 12990, 'em_dia', '2024-11-22'),
      (gen_random_uuid()::text, 'Paulo Bastos', 'paulo.b@email.com', 'mensal', 15990, 'pendente', '2026-08-09')
    ) AS v(id, nome, email, plano, fee, pay, desde)
    """,
    f"""
    INSERT INTO alunos (academia_id, nome, email, plano, mensalidade_centavos, situacao, matriculado_em)
    SELECT '{IRON}', 'Aluno ' || lpad(g::text, 3, '0'), 'aluno' || g || '@email.com',
           (ARRAY['mensal','trimestral','anual'])[1 + g % 3]::plano_aluno,
           (ARRAY[15990, 13990, 12990])[1 + g % 3],
           (CASE WHEN g % 25 = 0 THEN 'atrasado' WHEN g % 12 = 0 THEN 'pendente' ELSE 'em_dia' END)::situacao_pagamento,
           (CURRENT_DATE - (30 + g * 6)::int)
    FROM generate_series(1, 110) g
    """,
    # --- check-ins dos últimos 28 dias (frequência semanal varia por aluno)
    f"""
    INSERT INTO check_ins (academia_id, aluno_id, entrada_em)
    SELECT a.academia_id, a.id,
           date_trunc('day', now()) - (d || ' days')::interval + ((6 + floor(random() * 15)) || ' hours')::interval
    FROM (SELECT id, academia_id, 1 + (abs(hashtext(id::text)) % 6) AS freq,
                 abs(hashtext(email)) % 7 AS off FROM alunos WHERE academia_id = '{IRON}') a
    CROSS JOIN generate_series(0, 27) d
    WHERE ((d + a.off) % 7) < a.freq
    """,
    # --- telas
    f"""
    INSERT INTO telas (id, academia_id, sala, resolucao, status, pareada_em, ultimo_heartbeat) VALUES
      ('a1000000-0000-0000-0000-000000000001', '{IRON}', 'Sala de musculação', '1920x1080', 'online', now() - interval '90 days', now()),
      ('a1000000-0000-0000-0000-000000000002', '{IRON}', 'Área de cardio', '1920x1080', 'online', now() - interval '90 days', now()),
      ('a1000000-0000-0000-0000-000000000003', '{IRON}', 'Sala de funcional', '1366x768', 'online', now() - interval '60 days', now()),
      ('a1000000-0000-0000-0000-000000000004', '{POWER}', 'Sala principal', '1920x1080', 'online', now() - interval '60 days', now()),
      ('a1000000-0000-0000-0000-000000000005', '{STUDIO}', 'Sala principal', '1920x1080', 'online', now() - interval '60 days', now())
    """,
    # --- campanhas (as do Nutri Prime aparecem no painel do anunciante)
    f"""
    INSERT INTO campanhas_ads (id, anunciante_id, academia_id, nome, desconto_rotulo, manchete, corpo, cupom,
                               status, inicio, hora_inicio, hora_fim, orcamento_centavos, cpm_centavos) VALUES
      ('c1000000-0000-0000-0000-000000000001', '{NUTRI}', '{IRON}', '15% OFF linha de whey', '15%', 'OFF em toda a linha de whey', 'Aproveite o descanso! Ganhe 15% OFF na loja parceira.', 'PRIME15', 'ativa', CURRENT_DATE - 60, '06:00', '22:00', 400000, 10),
      ('c1000000-0000-0000-0000-000000000002', '{NUTRI}', '{IRON}', 'Combo creatina + coqueteleira', '10%', 'OFF no combo', 'Combo creatina e coqueteleira com desconto.', 'COMBO10', 'ativa', CURRENT_DATE - 45, '17:00', '21:00', 200000, 10),
      ('c1000000-0000-0000-0000-000000000003', '{NUTRI}', '{POWER}', 'Frete grátis acima de R$ 150', 'Frete', 'grátis acima de R$ 150', 'Frete grátis em compras acima de R$ 150.', 'FRETE150', 'pausada', CURRENT_DATE - 40, '06:00', '22:00', 200000, 10),
      ('c1000000-0000-0000-0000-000000000004', '{NUTRI}', '{STUDIO}', 'Pré-treino 20% OFF', '20%', 'OFF no pré-treino', 'Pré-treino com 20% OFF para alunos.', 'PRE20', 'ativa', CURRENT_DATE - 30, '06:00', '10:00', 150000, 10),
      ('c1000000-0000-0000-0000-000000000005', '{ACAI}', '{IRON}', 'Tigela pós-treino', '20%', 'OFF na tigela pós-treino', 'Recupere as energias com 20% OFF.', 'ACAI20', 'ativa', CURRENT_DATE - 30, '06:00', '22:00', 150000, 10),
      ('c1000000-0000-0000-0000-000000000006', '{FISIO}', '{IRON}', 'Avaliação postural', '1ª', 'sessão de avaliação sem custo', 'Agende uma avaliação postural gratuita.', 'MOVE01', 'ativa', CURRENT_DATE - 30, '06:00', '22:00', 100000, 10),
      ('c1000000-0000-0000-0000-000000000007', '{IRONWEAR}', '{IRON}', 'Coleção de treino', '25%', 'OFF na coleção de treino', 'Camisetas dry-fit e leggings com 25% OFF.', 'IRON25', 'ativa', CURRENT_DATE - 30, '06:00', '22:00', 200000, 10)
    """,
    # --- impressões: 30 dias, mais volume no fim do dia
    f"""
    INSERT INTO impressoes (academia_id, campanha_id, tela_id, nonce, custo_centavos, exibida_em)
    SELECT c.academia_id, c.id,
           (SELECT id FROM telas t WHERE t.academia_id = c.academia_id ORDER BY t.id LIMIT 1),
           md5(random()::text || clock_timestamp()::text || g::text),
           10,
           date_trunc('day', now()) - (d || ' days')::interval
             + ((CASE WHEN random() < 0.4 THEN 18 + floor(random() * 3)
                      WHEN random() < 0.5 THEN 6 + floor(random() * 3)
                      ELSE 9 + floor(random() * 9) END) || ' hours')::interval
             + (floor(random() * 3600) || ' seconds')::interval
    FROM campanhas_ads c
    CROSS JOIN generate_series(0, 29) d
    CROSS JOIN generate_series(1, 70) g
    WHERE c.academia_id IN ({ids(ACADEMIAS)})
      AND (c.status = 'ativa' OR d > 10)
      AND random() < 0.9
    """,
    # --- scans (~9% das impressões) e resgates (~32% dos scans)
    """
    INSERT INTO scans (academia_id, impressao_id, aluno_id, escaneado_em, resgatado_em, valor_compra_centavos)
    SELECT i.academia_id, i.id, NULL, i.exibida_em + interval '20 seconds',
           CASE WHEN random() < 0.32 THEN i.exibida_em + interval '3 hours' END,
           CASE WHEN random() < 0.32 THEN 4000 + floor(random() * 5000)::int END
    FROM impressoes i WHERE random() < 0.09
    """,
    # --- financeiro da academia Iron Factory (3 meses)
    f"""
    INSERT INTO lancamentos (academia_id, origem, descricao, valor_centavos, status, competencia, criado_em, liquidado_em) VALUES
      ('{IRON}', 'mensalidade', 'Mensalidades · lote diário (38 cobranças)', 523620, 'liquidado', date_trunc('month', CURRENT_DATE), now() - interval '5 days', now() - interval '5 days'),
      ('{IRON}', 'anuncio', 'Nutri Prime Suplementos · campanha whey', 148000, 'liquidado', date_trunc('month', CURRENT_DATE), now() - interval '6 days', now() - interval '6 days'),
      ('{IRON}', 'jukebox', 'Jukebox · pedidos avulsos da semana', 31200, 'liquidado', date_trunc('month', CURRENT_DATE), now() - interval '8 days', now() - interval '8 days'),
      ('{IRON}', 'anuncio', 'Açaí do Ponto · campanha tigela pós-treino', 86000, 'a_receber', date_trunc('month', CURRENT_DATE), now() - interval '10 days', NULL),
      ('{IRON}', 'mensalidade', 'Mensalidades · retentativa de cobrança', 47970, 'recusado', date_trunc('month', CURRENT_DATE), now() - interval '12 days', NULL),
      ('{IRON}', 'anuncio', 'Fisio Movimento · avaliação postural', 64000, 'liquidado', date_trunc('month', CURRENT_DATE), now() - interval '15 days', now() - interval '15 days'),
      ('{IRON}', 'mensalidade', 'Mensalidades · fechamento do mês', 5612000, 'liquidado', date_trunc('month', CURRENT_DATE) - interval '1 month', now() - interval '35 days', now() - interval '35 days'),
      ('{IRON}', 'anuncio', 'Anúncios · repasse do mês', 648000, 'liquidado', date_trunc('month', CURRENT_DATE) - interval '1 month', now() - interval '35 days', now() - interval '35 days'),
      ('{IRON}', 'jukebox', 'Jukebox · pedidos do mês', 118000, 'liquidado', date_trunc('month', CURRENT_DATE) - interval '1 month', now() - interval '35 days', now() - interval '35 days'),
      ('{IRON}', 'mensalidade', 'Mensalidades · fechamento do mês', 5387000, 'liquidado', date_trunc('month', CURRENT_DATE) - interval '2 month', now() - interval '65 days', now() - interval '65 days'),
      ('{IRON}', 'anuncio', 'Anúncios · repasse do mês', 521000, 'liquidado', date_trunc('month', CURRENT_DATE) - interval '2 month', now() - interval '65 days', now() - interval '65 days'),
      ('{IRON}', 'jukebox', 'Jukebox · pedidos do mês', 101000, 'liquidado', date_trunc('month', CURRENT_DATE) - interval '2 month', now() - interval '65 days', now() - interval '65 days')
    """,
    f"""
    INSERT INTO repasses (academia_id, anunciante_id, bruto_centavos, taxa_centavos, liquido_centavos, status, competencia, criado_em, pago_em) VALUES
      ('{IRON}', '{NUTRI}', 148000, 59200, 88800, 'pago', date_trunc('month', CURRENT_DATE), now() - interval '5 days', now() - interval '5 days'),
      ('{IRON}', '{ACAI}', 86000, 34400, 51600, 'em_transito', date_trunc('month', CURRENT_DATE), now() - interval '10 days', NULL),
      ('{IRON}', '{FISIO}', 64000, 25600, 38400, 'pago', date_trunc('month', CURRENT_DATE), now() - interval '15 days', now() - interval '15 days'),
      ('{IRON}', '{IRONWEAR}', 112000, 44800, 67200, 'pago', date_trunc('month', CURRENT_DATE), now() - interval '18 days', now() - interval '18 days')
    """,
    # --- créditos do anunciante Nutri Prime (recargas + consumo)
    f"""
    INSERT INTO creditos_anunciante (anunciante_id, valor_centavos, descricao, nota_fiscal, criado_em) VALUES
      ('{NUTRI}', 200000, 'Recarga de crédito · Stripe', 'NF 1042', now() - interval '5 days'),
      ('{NUTRI}', -128400, 'Consumo de impressões · 1ª quinzena', 'NF 1031', now() - interval '12 days'),
      ('{NUTRI}', 150000, 'Recarga de crédito · Stripe', 'NF 1018', now() - interval '19 days'),
      ('{NUTRI}', -110600, 'Consumo de impressões · 2ª quinzena', 'NF 0994', now() - interval '27 days'),
      ('{NUTRI}', 100000, 'Recarga de crédito · boleto', NULL, now() - interval '34 days')
    """,
    # --- jukebox
    """
    INSERT INTO faixas (id, titulo, artista, duracao_segundos, provedor, provedor_id) VALUES
      ('f1000000-0000-0000-0000-000000000001', 'Não Vou Parar', 'Bloco do Ritmo', 192, 'demo', 'd1'),
      ('f1000000-0000-0000-0000-000000000002', 'Peso Morto', 'Trio Cadência', 178, 'demo', 'd2'),
      ('f1000000-0000-0000-0000-000000000003', 'Meia Noite no Cardio', 'Áurea Base', 224, 'demo', 'd3'),
      ('f1000000-0000-0000-0000-000000000004', 'Série Final', 'Coletivo Norte', 242, 'demo', 'd4'),
      ('f1000000-0000-0000-0000-000000000005', 'Sem Intervalo', 'Mila Duarte', 201, 'demo', 'd5')
    """,
    f"""
    INSERT INTO jukebox_pedidos (academia_id, faixa_id, aluno_id, pedido_em)
    SELECT '{IRON}', f.id, a.id, now() - (f.ord || ' minutes')::interval
    FROM (SELECT id, row_number() OVER (ORDER BY id) AS ord FROM faixas WHERE provedor = 'demo') f
    JOIN (SELECT id, row_number() OVER (ORDER BY nome) AS ord FROM alunos
          WHERE academia_id = '{IRON}' AND nome IN ('Marina Rodrigues','Diego Santana','Camila Teixeira','Rafael Lima','Júlia Prado')) a
      ON a.ord = f.ord
    """,
]


async def main() -> None:
    engine = create_async_engine(settings.migrations_database_url)
    async with engine.begin() as conn:
        for stmt in LIMPAR + SEED:
            await conn.execute(text(stmt))
    await engine.dispose()
    print("Dados demo criados.")


if __name__ == "__main__":
    asyncio.run(main())
