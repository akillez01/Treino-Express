"""Garante que o isolamento multi-tenant funciona de ponta a ponta: via API
(RLS + SET LOCAL por request) e diretamente no Postgres (RLS sozinho, sem
depender da lógica do FastAPI)."""

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import auth_header


async def test_aluno_nao_acessa_treino_de_outra_academia(client, duas_academias):
    resp = await client.post(
        "/v1/treinos/gerar",
        json={"minutos": 30, "foco": "pernas"},
        headers=auth_header(duas_academias["token_a"]),
    )
    assert resp.status_code == 200
    treino_id = resp.json()["treino_id"]

    # Aluno da academia B tenta agir sobre um treino da academia A usando um
    # token válido (assinado corretamente, só que de outro tenant).
    resp_cross = await client.post(
        f"/v1/treinos/{treino_id}/exercicio/1/concluir",
        headers=auth_header(duas_academias["token_b"]),
    )
    assert resp_cross.status_code == 404

    # O dono de fato consegue.
    resp_owner = await client.post(
        f"/v1/treinos/{treino_id}/exercicio/1/concluir",
        headers=auth_header(duas_academias["token_a"]),
    )
    assert resp_owner.status_code == 200


async def test_ambas_academias_veem_o_catalogo_global(client, duas_academias):
    for token in (duas_academias["token_a"], duas_academias["token_b"]):
        resp = await client.post(
            "/v1/treinos/gerar",
            json={"minutos": 20, "foco": "ombros"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["exercicios"]) >= 1


@pytest.mark.parametrize("execucao", range(2))
async def test_set_local_nao_vaza_entre_sessoes_no_pool(execucao):
    """Sem `SET LOCAL`/`set_config(..., true)` ativo, uma nova sessão do pool
    não deve herdar `app.academia_id` de uma sessão anterior — a garantia
    central de `app/db/tenant.py`. Roda duas vezes (parametrize) para forçar
    reuso de conexão do mesmo pool do engine."""
    from app.db.session import AsyncSessionLocal

    tenant_id = uuid.uuid4()

    async with AsyncSessionLocal() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.academia_id', :id, true)"), {"id": str(tenant_id)}
        )
        current = await session.execute(text("SELECT current_setting('app.academia_id', true)"))
        assert current.scalar() == str(tenant_id)

    # Nova sessão/transação, nenhum set_config chamado — não deve ver o valor
    # setado acima (a transação anterior já terminou, o que já invalida um
    # `SET LOCAL`/`set_config(..., true)`).
    async with AsyncSessionLocal() as session, session.begin():
        current = await session.execute(text("SELECT current_setting('app.academia_id', true)"))
        assert current.scalar() in (None, "")


async def test_rls_bloqueia_no_nivel_do_postgres_sem_passar_pela_api(
    admin_sessionmaker, duas_academias
):
    """Confirma que a garantia vem do banco (RLS), não só da lógica do
    FastAPI: conecta como a role de runtime (`treino_app`), seta o tenant A,
    e tenta enxergar um aluno da academia B via SELECT direto."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    app_engine = create_async_engine(settings.database_url)
    async with app_engine.connect() as conn, conn.begin():
        await conn.execute(
            text("SELECT set_config('app.academia_id', :id, true)"),
            {"id": str(duas_academias["academia_a"])},
        )
        result = await conn.execute(
            text("SELECT id FROM alunos WHERE id = :aluno_b_id"),
            {"aluno_b_id": str(duas_academias["aluno_b"])},
        )
        assert result.first() is None  # RLS esconde a linha, mesmo existindo
    await app_engine.dispose()
