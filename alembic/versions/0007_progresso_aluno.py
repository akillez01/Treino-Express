"""progresso do aluno: meta semanal e esforço percebido ao fim do treino

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "ALTER TABLE alunos ADD COLUMN meta_semanal SMALLINT NOT NULL DEFAULT 3 "
        "CHECK (meta_semanal BETWEEN 1 AND 7)"
    )
    bind.exec_driver_sql(
        "ALTER TABLE treinos ADD COLUMN esforco SMALLINT CHECK (esforco BETWEEN 1 AND 5)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX idx_treinos_aluno_concluido ON treinos (aluno_id, concluido_em DESC) "
        "WHERE concluido_em IS NOT NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP INDEX idx_treinos_aluno_concluido")
    bind.exec_driver_sql("ALTER TABLE treinos DROP COLUMN esforco")
    bind.exec_driver_sql("ALTER TABLE alunos DROP COLUMN meta_semanal")
