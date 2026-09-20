"""treino_exercicios: descanso personalizado pelo aluno

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "ALTER TABLE treino_exercicios ADD COLUMN descanso_segundos SMALLINT "
        "CHECK (descanso_segundos IS NULL OR descanso_segundos BETWEEN 15 AND 300)"
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql("ALTER TABLE treino_exercicios DROP COLUMN descanso_segundos")
