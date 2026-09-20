"""funções SECURITY DEFINER para rotas sem tenant: pareamento de TV e scan de QR

Duas operações acontecem antes de existir um tenant na sessão: a TV informa o
código de 6 dígitos (ainda não sabemos a academia) e o aluno abre o link do QR
(sem login). A role de runtime está sujeita a RLS, então essas duas buscas
cruzadas rodam em funções mínimas com privilégio do dono, que só fazem o que
o nome diz e nada além.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

PARAR_TELA = """
CREATE OR REPLACE FUNCTION parear_tela(p_codigo TEXT)
RETURNS TABLE (tela_id UUID, academia_id UUID)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    RETURN QUERY
    UPDATE telas t
       SET pareada_em = now(), codigo_pareamento = NULL, status = 'online', ultimo_heartbeat = now()
     WHERE t.codigo_pareamento = upper(p_codigo) AND t.pareada_em IS NULL
    RETURNING t.id, t.academia_id;
END $$
"""

REGISTRAR_SCAN = """
CREATE OR REPLACE FUNCTION registrar_scan(p_campanha UUID, p_nonce TEXT)
RETURNS TABLE (marca TEXT, desconto TEXT, manchete TEXT, corpo TEXT, cupom TEXT)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_imp BIGINT; v_acad UUID;
BEGIN
    SELECT i.id, i.academia_id INTO v_imp, v_acad
      FROM impressoes i WHERE i.campanha_id = p_campanha AND i.nonce = p_nonce;
    IF v_imp IS NULL THEN
        RETURN;
    END IF;
    -- um QR fotografado não conta duas vezes: só o primeiro scan da exibição
    IF NOT EXISTS (SELECT 1 FROM scans s WHERE s.impressao_id = v_imp) THEN
        INSERT INTO scans (academia_id, impressao_id) VALUES (v_acad, v_imp);
    END IF;
    RETURN QUERY
    SELECT an.nome, c.desconto_rotulo, c.manchete, c.corpo, c.cupom
      FROM campanhas_ads c JOIN anunciantes an ON an.id = c.anunciante_id
     WHERE c.id = p_campanha;
END $$
"""


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(PARAR_TELA)
    bind.exec_driver_sql(REGISTRAR_SCAN)
    bind.exec_driver_sql("REVOKE ALL ON FUNCTION parear_tela(TEXT) FROM PUBLIC")
    bind.exec_driver_sql("REVOKE ALL ON FUNCTION registrar_scan(UUID, TEXT) FROM PUBLIC")
    bind.exec_driver_sql("GRANT EXECUTE ON FUNCTION parear_tela(TEXT) TO treino_app")
    bind.exec_driver_sql("GRANT EXECUTE ON FUNCTION registrar_scan(UUID, TEXT) TO treino_app")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP FUNCTION registrar_scan(UUID, TEXT)")
    bind.exec_driver_sql("DROP FUNCTION parear_tela(TEXT)")
