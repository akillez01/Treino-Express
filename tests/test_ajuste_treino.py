"""Ajustes do aluno no treino: carga, séries, descanso, trocar e remover."""

from tests.conftest import auth_header


async def _gerar(client, token, minutos=30, foco="pernas"):
    r = await client.post(
        "/v1/treinos/gerar", json={"minutos": minutos, "foco": foco}, headers=auth_header(token)
    )
    assert r.status_code == 200
    return r.json()


async def test_ajusta_carga_series_e_descanso(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    treino = await _gerar(client, duas_academias["token_a"])
    tid = treino["treino_id"]

    r = await client.patch(
        f"/v1/treinos/{tid}/exercicio/1",
        json={"carga": "Carga 40 kg", "series": "5x5", "descanso_segundos": 90},
        headers=h,
    )
    assert r.status_code == 200
    e1, e2 = r.json()["exercicios"][0], r.json()["exercicios"][1]
    assert (e1["carga"], e1["series"], e1["descanso_segundos"]) == ("Carga 40 kg", "5x5", 90)
    assert e2["descanso_segundos"] != 90  # só o exercício ajustado mudou

    # o descanso registrado usa o valor personalizado
    d = await client.post(f"/v1/treinos/{tid}/descanso", json={"ordem": 1}, headers=h)
    assert d.json()["descanso_segundos"] == 90


async def test_aplica_descanso_a_todos(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    tid = (await _gerar(client, duas_academias["token_a"]))["treino_id"]
    r = await client.patch(
        f"/v1/treinos/{tid}/exercicio/2",
        json={"descanso_segundos": 45, "aplicar_descanso_a_todos": True},
        headers=h,
    )
    assert {e["descanso_segundos"] for e in r.json()["exercicios"]} == {45}


async def test_valida_limites_do_descanso(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    tid = (await _gerar(client, duas_academias["token_a"]))["treino_id"]
    for valor in (5, 999):
        r = await client.patch(
            f"/v1/treinos/{tid}/exercicio/1", json={"descanso_segundos": valor}, headers=h
        )
        assert r.status_code == 422


async def test_troca_por_alternativa_do_mesmo_foco(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    treino = await _gerar(client, duas_academias["token_a"], minutos=20)  # 3 exercícios
    tid = treino["treino_id"]
    alt = await client.get(f"/v1/treinos/{tid}/exercicio/1/alternativas", headers=h)
    assert alt.status_code == 200 and alt.json()
    nomes_no_treino = {e["nome"] for e in treino["exercicios"]}
    assert all(a["nome"] not in nomes_no_treino for a in alt.json())

    novo = alt.json()[0]
    r = await client.put(
        f"/v1/treinos/{tid}/exercicio/1/trocar",
        json={"exercicio_id": novo["exercicio_id"]},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["exercicios"][0]["nome"] == novo["nome"]


async def test_nao_troca_por_exercicio_de_outro_foco(client, duas_academias, admin_sessionmaker):
    from sqlalchemy import text

    h = auth_header(duas_academias["token_a"])
    tid = (await _gerar(client, duas_academias["token_a"], foco="pernas"))["treino_id"]
    async with admin_sessionmaker() as s:
        outro = (
            await s.execute(
                text(
                    "SELECT id::text FROM exercicios WHERE academia_id IS NULL "
                    "AND foco = 'ombros' LIMIT 1"
                )
            )
        ).scalar()
    r = await client.put(
        f"/v1/treinos/{tid}/exercicio/1/trocar", json={"exercicio_id": outro}, headers=h
    )
    assert r.status_code == 422


async def test_remove_exercicio_e_mantem_ao_menos_um(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    treino = await _gerar(client, duas_academias["token_a"], minutos=20)
    tid, n = treino["treino_id"], len(treino["exercicios"])
    ordens = [e["ordem"] for e in treino["exercicios"]]

    for ordem in ordens[:-1]:
        r = await client.delete(f"/v1/treinos/{tid}/exercicio/{ordem}", headers=h)
        assert r.status_code == 200
    assert len(r.json()["exercicios"]) == 1
    ultimo = await client.delete(f"/v1/treinos/{tid}/exercicio/{ordens[-1]}", headers=h)
    assert ultimo.status_code == 409
    assert n >= 2


async def test_outra_academia_nao_ajusta_treino_alheio(client, duas_academias):
    tid = (await _gerar(client, duas_academias["token_a"]))["treino_id"]
    hb = auth_header(duas_academias["token_b"])
    assert (
        await client.patch(f"/v1/treinos/{tid}/exercicio/1", json={"carga": "1 kg"}, headers=hb)
    ).status_code == 404
    assert (await client.delete(f"/v1/treinos/{tid}/exercicio/1", headers=hb)).status_code == 404
    assert (await client.get(f"/v1/treinos/{tid}", headers=hb)).status_code == 404
