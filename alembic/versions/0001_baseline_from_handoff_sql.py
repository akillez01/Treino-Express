"""baseline: schema completo do handoff (docs/04-banco-de-dados.sql) + patch

Executa o SQL do handoff quase verbatim via `exec_driver_sql` (bypassa o
parser de bind-params do SQLAlchemy — necessário porque o script tem blocos
`DO $$ ... $$` e uma function PL/pgSQL, e porque `::` de cast não deve virar
bind param). O patch no final amplia o enum `foco_muscular` para os 6 grupos
usados pelo design e adiciona `exercicios.imagem_url` (docs/07-catalogo-exercicios.md).

Revision ID: 0001
Revises:
Create Date: 2026-09-20
"""

import sys
from pathlib import Path

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sql_utils import split_sql_statements  # noqa: E402

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_PATH = Path(__file__).parent / "sql" / "0001_baseline.sql"


def upgrade() -> None:
    bind = op.get_bind()
    for statement in split_sql_statements(SQL_PATH.read_text()):
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    # Não reversível de forma granular — aceitável só para a baseline.
    # Nunca fazer isso em produção fora desta migration inicial.
    bind = op.get_bind()
    bind.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
