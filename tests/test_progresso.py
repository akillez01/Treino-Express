"""Desempenho do aluno: regras de cálculo e isolamento."""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.services import progresso_service as ps
from tests.conftest import auth_header


def test_extrai_carga_em_kg():
    assert ps._kg("Carga 25 kg") == 25
    assert ps._kg("2x14 kg") == 14
    assert ps._kg("Barra W 15,5 kg") == 15.5
    assert ps._kg("Peso do corpo") is None
    assert ps._kg(None) is None


def test_volume_usa_series_repeticoes_e_carga():
    assert ps._volume("Carga 20 kg", "3x12") == 720
    assert ps._volume("Peso do corpo", "3x12") == 0
    assert ps._volume("Carga 20 kg", "12 min") == 0


def test_sequencia_atual_e_melhor():
    hoje = date(2026, 9, 20)
    dias = {hoje - timedelta(days=i) for i in (0, 1, 2)} | {
        hoje - timedelta(days=i) for i in (10, 11, 12, 13)
    }
    assert ps._sequencias(dias, hoje) == (3, 4)
    # sem treinar ontem nem hoje: a sequência atual zera, a melhor permanece
    assert ps._sequencias({hoje - timedelta(days=5), hoje - timedelta(days=4)}, hoje) == (0, 2)
    # treinou até ontem: ainda conta
    assert ps._sequencias({hoje - timedelta(days=1)}, hoje) == (1, 1)
    assert ps._sequencias(set(), hoje) == (0, 0)


@pytest.fixture
async def historico(admin_sessionmaker, duas_academias):
    """Três treinos concluídos do aluno A, com carga subindo no mesmo exercício."""
    a, aluno = str(duas_academias["academia_a"]), str(duas_academias["aluno_a"])
    async with admin_sessionmaker() as s, s.begin():
        ex = (
            await s.execute(
                text(
                    "INSERT INTO exercicios (nome, foco, series_padrao, carga_sugerida) "
                    "VALUES ('Supino teste', 'peito_triceps', '3x10', 'Barra 40 kg') RETURNING id::text"
                )
            )
        ).scalar()
        for dias_atras, kg in ((6, 40), (3, 45), (0, 50)):
            t = (
                await s.execute(
                    text(
                        "INSERT INTO treinos (academia_id, aluno_id, minutos_disponiveis, foco, "
                        "iniciado_em, concluido_em) VALUES (:a, :al, 30, 'peito_triceps', "
                        "now() - make_interval(days => :d, mins => 40), now() - make_interval(days => :d)) "
                        "RETURNING id::text"
                    ),
                    {"a": a, "al": aluno, "d": dias_atras},
                )
            ).scalar()
            await s.execute(
                text(
                    "INSERT INTO treino_exercicios (treino_id, exercicio_id, ordem, series, carga, concluido_em) "
                    "VALUES (CAST(:t AS uuid), CAST(:e AS uuid), 1, '3x10', :c, "
                    "now() - make_interval(days => :d))"
                ),
                {"t": t, "e": ex, "c": f"Barra {kg} kg", "d": dias_atras},
            )
    return duas_academias


async def test_progresso_calcula_evolucao(client, historico):
    r = await client.get("/v1/progresso", headers=auth_header(historico["token_a"]))
    assert r.status_code == 200
    d = r.json()
    assert d["totais"]["treinos"] == 3
    assert d["totais"]["volume_kg"] == (40 + 45 + 50) * 30
    rec = d["recordes"][0]
    assert (rec["exercicio"], rec["kg"], rec["evolucao_kg"]) == ("Supino teste", 50, 10)
    assert [p["kg"] for p in d["evolucao_carga"][0]["pontos"]] == [40, 45, 50]
    ids = {c["id"] for c in d["conquistas"] if c["conquistada"]}
    assert {"primeiro_treino", "novo_recorde"} <= ids
    assert 0 <= d["pontuacao"]["total"] <= 100


async def test_progresso_e_isolado_por_aluno(client, historico):
    r = await client.get("/v1/progresso", headers=auth_header(historico["token_b"]))
    assert r.json()["totais"]["treinos"] == 0
    assert r.json()["recordes"] == []


async def test_meta_semanal_e_avaliacao(client, historico, admin_sessionmaker):
    h = auth_header(historico["token_a"])
    assert (
        await client.put("/v1/progresso/meta", json={"meta_semanal": 5}, headers=h)
    ).status_code == 200
    assert (
        await client.put("/v1/progresso/meta", json={"meta_semanal": 9}, headers=h)
    ).status_code == 422
    assert (await client.get("/v1/progresso", headers=h)).json()["meta_semanal"] == 5

    async with admin_sessionmaker() as s:
        tid = (
            await s.execute(
                text("SELECT id::text FROM treinos WHERE aluno_id = :a LIMIT 1"),
                {"a": str(historico["aluno_a"])},
            )
        ).scalar()
    assert (
        await client.post(f"/v1/treinos/{tid}/avaliar", json={"esforco": 4}, headers=h)
    ).status_code == 204
    assert (
        await client.post(f"/v1/treinos/{tid}/avaliar", json={"esforco": 9}, headers=h)
    ).status_code == 422
    # outro aluno não avalia treino alheio
    hb = auth_header(historico["token_b"])
    assert (
        await client.post(f"/v1/treinos/{tid}/avaliar", json={"esforco": 3}, headers=hb)
    ).status_code == 404
    assert (await client.get(f"/v1/treinos/{tid}/resumo", headers=hb)).status_code == 404
    res = (await client.get(f"/v1/treinos/{tid}/resumo", headers=h)).json()
    assert res["esforco"] == 4 and res["exercicios_concluidos"] == 1
