from tests.conftest import auth_header


async def test_fluxo_completo_gerar_descansar_concluir(client, duas_academias):
    token = duas_academias["token_a"]

    resp = await client.post(
        "/v1/treinos/gerar", json={"minutos": 30, "foco": "pernas"}, headers=auth_header(token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["minutos"] == 30
    assert body["foco"] == "pernas"
    assert 3 <= len(body["exercicios"]) <= 6
    treino_id = body["treino_id"]

    resp = await client.post(
        f"/v1/treinos/{treino_id}/descanso", json={"ordem": 1}, headers=auth_header(token)
    )
    assert resp.status_code == 200
    assert resp.json()["descanso_segundos"] > 0
    # Sem ninguém populando ads:rotation:{academia_id} no Redis, o card de
    # anúncio simplesmente não aparece — comportamento esperado (docs/03).
    assert resp.json()["campanha"] is None

    resp = await client.post(
        f"/v1/treinos/{treino_id}/exercicio/1/concluir", headers=auth_header(token)
    )
    assert resp.status_code == 200
    assert resp.json()["treino_concluido"] is False
    assert resp.json()["proximo_ordem"] == 2


async def test_gerar_treino_sem_token_e_401(client):
    resp = await client.post("/v1/treinos/gerar", json={"minutos": 30, "foco": "pernas"})
    assert resp.status_code == 401


async def test_gerar_treino_minutos_fora_da_faixa_e_422(client, duas_academias):
    resp = await client.post(
        "/v1/treinos/gerar",
        json={"minutos": 5, "foco": "pernas"},
        headers=auth_header(duas_academias["token_a"]),
    )
    assert resp.status_code == 422
