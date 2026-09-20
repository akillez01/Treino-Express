"""metas por exercício, ranking (opt-in) e lembretes por WhatsApp (opt-in)

Ranking e lembretes só valem para quem aceitou: `ranking_visivel` e
`lembretes_whatsapp` começam FALSE. Volume do treino é gravado ao concluir, para
o ranking não recalcular o histórico inteiro a cada consulta.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

STATEMENTS = [
    "ALTER TABLE alunos ADD COLUMN ranking_visivel BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE alunos ADD COLUMN lembretes_whatsapp BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE treinos ADD COLUMN volume_kg NUMERIC(10,1)",
    """
    CREATE TABLE metas_exercicio (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        academia_id   UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
        aluno_id      UUID        NOT NULL REFERENCES alunos(id)    ON DELETE CASCADE,
        exercicio     TEXT        NOT NULL,
        alvo_kg       NUMERIC(6,1) NOT NULL CHECK (alvo_kg > 0),
        prazo         DATE,
        criada_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
        atingida_em   TIMESTAMPTZ,
        UNIQUE (aluno_id, exercicio)
    )
    """,
    "CREATE INDEX idx_metas_aluno ON metas_exercicio (aluno_id)",
    """
    CREATE TABLE lembretes (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        academia_id   UUID        NOT NULL REFERENCES academias(id) ON DELETE CASCADE,
        aluno_id      UUID        NOT NULL REFERENCES alunos(id)    ON DELETE CASCADE,
        tipo          TEXT        NOT NULL DEFAULT 'sequencia_quebrada',
        canal         TEXT        NOT NULL DEFAULT 'whatsapp',
        status        TEXT        NOT NULL CHECK (status IN ('enviado', 'simulado', 'falhou')),
        mensagem      TEXT        NOT NULL,
        erro          TEXT,
        criado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX idx_lembretes_aluno ON lembretes (aluno_id, criado_em DESC)",
    "CREATE INDEX idx_lembretes_academia ON lembretes (academia_id, criado_em DESC)",
]

for tabela in ("metas_exercicio", "lembretes"):
    STATEMENTS += [
        f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY tenant_isolation ON {tabela} "
        "USING (academia_id = tenant_atual()) WITH CHECK (academia_id = tenant_atual())",
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for stmt in STATEMENTS:
        bind.exec_driver_sql(stmt)
    # tabelas novas: a role de runtime precisa dos mesmos privilégios das demais
    bind.exec_driver_sql(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON metas_exercicio, lembretes TO treino_app"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE lembretes")
    bind.exec_driver_sql("DROP TABLE metas_exercicio")
    bind.exec_driver_sql("ALTER TABLE treinos DROP COLUMN volume_kg")
    bind.exec_driver_sql("ALTER TABLE alunos DROP COLUMN lembretes_whatsapp")
    bind.exec_driver_sql("ALTER TABLE alunos DROP COLUMN ranking_visivel")
