"""define a senha da role treino_app a partir de APP_DB_PASSWORD

A baseline cria treino_app com senha de dev. Em produção a senha vem do
ambiente; se a variável não existir (dev/testes) nada muda.

Revision ID: 0002
Revises: 0001
"""

import os

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    password = os.environ.get("APP_DB_PASSWORD")
    if not password:
        return
    escaped = password.replace("'", "''")
    op.get_bind().exec_driver_sql(f"ALTER ROLE treino_app PASSWORD '{escaped}'")


def downgrade() -> None:
    pass
