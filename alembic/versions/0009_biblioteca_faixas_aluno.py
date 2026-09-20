"""Biblioteca pessoal de faixas do aluno.

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        CREATE TABLE aluno_biblioteca_faixas (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            aluno_id           UUID        NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
            spotify_id         TEXT        NOT NULL,
            titulo             TEXT        NOT NULL,
            artista            TEXT        NOT NULL,
            duracao_segundos   SMALLINT    NOT NULL,
            capa_url           TEXT,
            adicionada_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (aluno_id, spotify_id)
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE INDEX idx_aluno_biblioteca_faixas_aluno "
        "ON aluno_biblioteca_faixas (aluno_id, adicionada_em DESC)"
    )
    bind.exec_driver_sql("ALTER TABLE aluno_biblioteca_faixas ENABLE ROW LEVEL SECURITY")
    bind.exec_driver_sql("ALTER TABLE aluno_biblioteca_faixas FORCE ROW LEVEL SECURITY")
    bind.exec_driver_sql(
        """
        CREATE POLICY tenant_isolation ON aluno_biblioteca_faixas
            USING (EXISTS (
                SELECT 1 FROM alunos
                WHERE alunos.id = aluno_biblioteca_faixas.aluno_id
                  AND alunos.academia_id = tenant_atual()
            ))
            WITH CHECK (EXISTS (
                SELECT 1 FROM alunos
                WHERE alunos.id = aluno_biblioteca_faixas.aluno_id
                  AND alunos.academia_id = tenant_atual()
            ))
        """
    )
    bind.exec_driver_sql(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON aluno_biblioteca_faixas TO treino_app"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP TABLE aluno_biblioteca_faixas")
