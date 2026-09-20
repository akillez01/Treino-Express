"""Painéis de gestor e anunciante: isolamento por tenant/anunciante via API."""

import uuid

import pytest
from sqlalchemy import text

from app.core.security import create_access_token
from tests.conftest import auth_header


@pytest.fixture
async def cenario(admin_sessionmaker, duas_academias):
    """Duas academias (do fixture) com uma tela cada, e dois anunciantes, cada
    um com uma campanha na academia A."""
    suf = uuid.uuid4().hex[:8]
    a, b = duas_academias["academia_a"], duas_academias["academia_b"]
    ids = {
        k: str(uuid.uuid4()) for k in ("tela_a", "tela_b", "anun_1", "anun_2", "camp_1", "camp_2")
    }
    async with admin_sessionmaker() as s, s.begin():
        for tela, ac, sala in ((ids["tela_a"], a, "Sala A"), (ids["tela_b"], b, "Sala B")):
            await s.execute(
                text(
                    "INSERT INTO telas (id, academia_id, sala, status, pareada_em) "
                    "VALUES (:id, :ac, :sala, 'online', now())"
                ),
                {"id": tela, "ac": str(ac), "sala": sala},
            )
        for an, nome in ((ids["anun_1"], "Anunciante 1"), (ids["anun_2"], "Anunciante 2")):
            await s.execute(
                text(
                    "INSERT INTO anunciantes (id, nome, email_contato, saldo_centavos) "
                    "VALUES (:id, :nome, :email, 1000)"
                ),
                {"id": an, "nome": nome, "email": f"{an[:8]}-{suf}@x.com"},
            )
        for camp, an in ((ids["camp_1"], ids["anun_1"]), (ids["camp_2"], ids["anun_2"])):
            await s.execute(
                text(
                    """INSERT INTO campanhas_ads (id, anunciante_id, academia_id, nome, desconto_rotulo,
                       manchete, corpo, cupom, status, inicio, orcamento_centavos)
                       VALUES (:id, :an, :ac, 'Camp', '10%', 'm', 'c', 'X', 'ativa', CURRENT_DATE, 1000)"""
                ),
                {"id": camp, "an": an, "ac": str(a)},
            )
    tok = {
        "gestor_a": create_access_token(subject=str(a), type="gestor", academia_id=a),
        "gestor_b": create_access_token(subject=str(b), type="gestor", academia_id=b),
        "anun_1": create_access_token(subject=ids["anun_1"], type="anunciante"),
        "anun_2": create_access_token(subject=ids["anun_2"], type="anunciante"),
    }
    return {**ids, **tok}


async def test_gestor_ve_so_as_telas_da_propria_academia(client, cenario):
    r = await client.get("/v1/academia/telas", headers=auth_header(cenario["gestor_a"]))
    assert r.status_code == 200
    assert [t["sala"] for t in r.json()["telas"]] == ["Sala A"]


async def test_gestor_nao_pausa_tela_de_outra_academia(client, cenario):
    r = await client.post(
        f"/v1/academia/telas/{cenario['tela_b']}/pausar", headers=auth_header(cenario["gestor_a"])
    )
    assert r.status_code == 404
    r = await client.post(
        f"/v1/academia/telas/{cenario['tela_a']}/pausar", headers=auth_header(cenario["gestor_a"])
    )
    assert r.status_code == 200 and r.json()["status"] == "pausada"


async def test_anunciante_ve_so_as_proprias_campanhas(client, cenario):
    r = await client.get("/v1/anunciante/campanhas", headers=auth_header(cenario["anun_1"]))
    assert r.status_code == 200
    assert [c["id"] for c in r.json()["campanhas"]] == [cenario["camp_1"]]
    assert r.json()["conta"]["nome"] == "Anunciante 1"


async def test_anunciante_nao_altera_campanha_de_outro(client, cenario):
    r = await client.patch(
        f"/v1/anunciante/campanhas/{cenario['camp_2']}",
        json={"ativa": False},
        headers=auth_header(cenario["anun_1"]),
    )
    assert r.status_code == 404
    r = await client.patch(
        f"/v1/anunciante/campanhas/{cenario['camp_1']}",
        json={"ativa": False},
        headers=auth_header(cenario["anun_1"]),
    )
    assert r.status_code == 200 and r.json()["status"] == "pausada"


async def test_perfis_nao_cruzam(client, cenario, duas_academias):
    aluno = duas_academias["token_a"]
    assert (await client.get("/v1/academia/resumo", headers=auth_header(aluno))).status_code == 403
    assert (
        await client.get("/v1/anunciante/campanhas", headers=auth_header(cenario["gestor_a"]))
    ).status_code == 403
    assert (
        await client.get("/v1/academia/resumo", headers=auth_header(cenario["anun_1"]))
    ).status_code == 403
