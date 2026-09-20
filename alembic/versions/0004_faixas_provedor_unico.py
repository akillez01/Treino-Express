"""faixas: uma linha por faixa de cada provedor (evita duplicar a mesma música do Spotify)

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        "CREATE UNIQUE INDEX uq_faixas_provedor ON faixas (provedor, provedor_id) "
        "WHERE provedor_id IS NOT NULL"
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("DROP INDEX uq_faixas_provedor")
