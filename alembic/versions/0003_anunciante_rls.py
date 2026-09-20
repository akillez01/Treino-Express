"""RLS por anunciante (painel do anunciante) e fechamento de tabelas sem RLS

O anunciante atua em várias academias, então o isolamento por academia não
serve para ele: o token do anunciante seta `app.anunciante_id` (e nenhuma
academia). As policies abaixo são permissivas (OR com as de tenant).

Também habilita RLS em `creditos_anunciante` e `anunciantes`, que estavam
abertas a qualquer sessão da role de runtime.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

STATEMENTS = [
    """
    CREATE OR REPLACE FUNCTION anunciante_atual() RETURNS UUID
    LANGUAGE sql STABLE AS $$
        SELECT NULLIF(current_setting('app.anunciante_id', TRUE), '')::UUID;
    $$
    """,
    # campanhas: o anunciante lê e atualiza (pausar) as suas
    """
    CREATE POLICY anunciante_campanhas ON campanhas_ads
        USING (anunciante_id = anunciante_atual())
        WITH CHECK (anunciante_id = anunciante_atual())
    """,
    """
    CREATE POLICY anunciante_impressoes ON impressoes FOR SELECT
        USING (EXISTS (
            SELECT 1 FROM campanhas_ads c
            WHERE c.id = impressoes.campanha_id AND c.anunciante_id = anunciante_atual()
        ))
    """,
    """
    CREATE POLICY anunciante_scans ON scans FOR SELECT
        USING (EXISTS (
            SELECT 1 FROM impressoes i
            JOIN campanhas_ads c ON c.id = i.campanha_id
            WHERE i.id = scans.impressao_id AND c.anunciante_id = anunciante_atual()
        ))
    """,
    """
    CREATE POLICY anunciante_repasses ON repasses FOR SELECT
        USING (anunciante_id = anunciante_atual())
    """,
    "ALTER TABLE creditos_anunciante ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE creditos_anunciante FORCE ROW LEVEL SECURITY",
    """
    CREATE POLICY anunciante_creditos ON creditos_anunciante
        USING (anunciante_id = anunciante_atual())
        WITH CHECK (anunciante_id = anunciante_atual())
    """,
    "ALTER TABLE anunciantes ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE anunciantes FORCE ROW LEVEL SECURITY",
    # o próprio anunciante, ou a academia que tem campanha dele
    """
    CREATE POLICY anunciante_visivel ON anunciantes FOR SELECT
        USING (
            id = anunciante_atual()
            OR EXISTS (
                SELECT 1 FROM campanhas_ads c
                WHERE c.anunciante_id = anunciantes.id AND c.academia_id = tenant_atual()
            )
        )
    """,
]


def upgrade() -> None:
    bind = op.get_bind()
    for stmt in STATEMENTS:
        bind.exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    for stmt in (
        "DROP POLICY anunciante_visivel ON anunciantes",
        "ALTER TABLE anunciantes NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE anunciantes DISABLE ROW LEVEL SECURITY",
        "DROP POLICY anunciante_creditos ON creditos_anunciante",
        "ALTER TABLE creditos_anunciante NO FORCE ROW LEVEL SECURITY",
        "ALTER TABLE creditos_anunciante DISABLE ROW LEVEL SECURITY",
        "DROP POLICY anunciante_repasses ON repasses",
        "DROP POLICY anunciante_scans ON scans",
        "DROP POLICY anunciante_impressoes ON impressoes",
        "DROP POLICY anunciante_campanhas ON campanhas_ads",
        "DROP FUNCTION anunciante_atual()",
    ):
        bind.exec_driver_sql(stmt)
