"""Metas por exercício, ranking (opt-in) e lembretes de sequência."""

from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import text

from app.core.security import create_access_token
from app.integrations.whatsapp import client as whatsapp
from app.services.ranking_service import nome_publico
from tests.conftest import auth_header


def _gestor(dados, chave="a"):
    ac = dados[f"academia_{chave}"]
    return create_access_token(subject=str(ac), type="gestor", academia_id=ac)


# ---------------------------------------------------------------- metas
async def test_meta_de_exercicio_aparece_no_progresso(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    amanha = (date.today() + timedelta(days=30)).isoformat()
    r = await client.put(
        "/v1/progresso/metas",
        json={"exercicio": "Supino Teste", "alvo_kg": 80, "prazo": amanha},
        headers=h,
    )
    assert r.status_code == 200
    metas = (await client.get("/v1/progresso", headers=h)).json()["metas"]
    assert metas[0]["exercicio"] == "Supino Teste"
    assert (metas[0]["alvo_kg"], metas[0]["atual_kg"], metas[0]["pct"]) == (80, 0, 0)
    assert metas[0]["dias_restantes"] == 30

    # outro aluno não vê a meta
    outra = (
        await client.get("/v1/progresso", headers=auth_header(duas_academias["token_b"]))
    ).json()
    assert outra["metas"] == []

    assert (
        await client.delete("/v1/progresso/metas?exercicio=Supino%20Teste", headers=h)
    ).status_code == 204
    assert (await client.get("/v1/progresso", headers=h)).json()["metas"] == []


async def test_meta_valida_prazo_e_peso(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    ontem = (date.today() - timedelta(days=1)).isoformat()
    ruim = {"exercicio": "Supino", "alvo_kg": 50, "prazo": ontem}
    assert (await client.put("/v1/progresso/metas", json=ruim, headers=h)).status_code == 422
    assert (
        await client.put(
            "/v1/progresso/metas", json={"exercicio": "Supino", "alvo_kg": 0}, headers=h
        )
    ).status_code == 422


# ---------------------------------------------------------- preferências
async def test_preferencias_exigem_telefone_valido(client, duas_academias):
    h = auth_header(duas_academias["token_a"])
    r = await client.put("/v1/aluno/preferencias", json={"lembretes_whatsapp": True}, headers=h)
    assert r.status_code == 422  # sem telefone
    r = await client.put("/v1/aluno/preferencias", json={"telefone": "123"}, headers=h)
    assert r.status_code == 422
    r = await client.put(
        "/v1/aluno/preferencias",
        json={"lembretes_whatsapp": True, "telefone": "(11) 99999-0000"},
        headers=h,
    )
    assert r.status_code == 200 and r.json()["telefone"] == "5511999990000"


def test_normaliza_telefone():
    assert whatsapp.normalizar_telefone("(11) 99999-0000") == "5511999990000"
    assert whatsapp.normalizar_telefone("+55 11 3333-4444") == "551133334444"
    assert whatsapp.normalizar_telefone("12345") is None


# ---------------------------------------------------------------- ranking
def test_nome_publico_mostra_so_inicial():
    assert nome_publico("Marina Rodrigues") == "Marina R."
    assert nome_publico("Ana Maria de Souza") == "Ana S."
    assert nome_publico("Cher") == "Cher"


async def _treino_concluido(s, academia, aluno, dias_atras, volume=100):
    await s.execute(
        text(
            "INSERT INTO treinos (academia_id, aluno_id, minutos_disponiveis, foco, iniciado_em, "
            "concluido_em, volume_kg) VALUES (:a, :al, 30, 'pernas', "
            "now() - make_interval(days => :d, mins => 40), now() - make_interval(days => :d), :v)"
        ),
        {"a": str(academia), "al": str(aluno), "d": dias_atras, "v": volume},
    )


async def test_ranking_so_para_quem_participa_e_isolado(client, duas_academias, admin_sessionmaker):
    d = duas_academias
    ha, hb = auth_header(d["token_a"]), auth_header(d["token_b"])

    # não participa: não vê a classificação
    r = (await client.get("/v1/ranking", headers=ha)).json()
    assert r["participando"] is False and r["itens"] == []

    async with admin_sessionmaker() as s, s.begin():
        for ac, al, dias in (
            (d["academia_a"], d["aluno_a"], (1, 2, 3)),
            (d["academia_b"], d["aluno_b"], (1,)),
        ):
            for x in dias:
                await _treino_concluido(s, ac, al, x)
        await s.execute(
            text("UPDATE alunos SET ranking_visivel = true WHERE id IN (:a, :b)"),
            {"a": str(d["aluno_a"]), "b": str(d["aluno_b"])},
        )

    ra = (await client.get("/v1/ranking?metrica=treinos", headers=ha)).json()
    rb = (await client.get("/v1/ranking?metrica=treinos", headers=hb)).json()
    # cada academia enxerga só os próprios alunos
    assert ra["total"] == 1 and ra["itens"][0]["valor"] == 3 and ra["itens"][0]["eu"] is True
    assert rb["total"] == 1 and rb["itens"][0]["valor"] == 1
    assert (await client.get("/v1/ranking?metrica=volume", headers=ha)).json()["itens"][0][
        "valor"
    ] == 300


# --------------------------------------------------------------- lembretes
@pytest.fixture
async def parado(admin_sessionmaker, duas_academias):
    """Aluno A treinou 3 dias seguidos e parou há 5 dias; aceitou lembretes."""
    d = duas_academias
    async with admin_sessionmaker() as s, s.begin():
        for x in (5, 6, 7, 12, 14):
            await _treino_concluido(s, d["academia_a"], d["aluno_a"], x)
        await s.execute(
            text(
                "UPDATE alunos SET lembretes_whatsapp = true, telefone = '5511999990001' WHERE id = :a"
            ),
            {"a": str(d["aluno_a"])},
        )
    return d


async def test_detecta_quem_quebrou_a_sequencia(client, parado):
    r = await client.get("/v1/academia/lembretes", headers=auth_header(_gestor(parado)))
    assert r.status_code == 200
    c = next(x for x in r.json()["candidatos"] if x["aluno_id"] == str(parado["aluno_a"]))
    assert c["dias_sem_treinar"] == 5 and c["sequencia_perdida"] == 3
    assert c["pode_enviar"] is True and c["telefone"].endswith("0001")
    assert "sequência de 3 dias" in c["mensagem"]
    # a outra academia não enxerga
    outra = await client.get("/v1/academia/lembretes", headers=auth_header(_gestor(parado, "b")))
    assert all(x["aluno_id"] != str(parado["aluno_a"]) for x in outra.json()["candidatos"])


async def test_envio_simulado_registra_e_respeita_cooldown(client, parado):
    h = auth_header(_gestor(parado))
    r = await client.post("/v1/academia/lembretes/enviar", json={}, headers=h)
    res = [x for x in r.json()["resultados"] if x["aluno_id"] == str(parado["aluno_a"])]
    assert res and res[0]["status"] == "simulado" and r.json()["simulado"] is True

    # segundo envio: em cooldown, nada novo
    r2 = await client.post("/v1/academia/lembretes/enviar", json={}, headers=h)
    assert all(x["aluno_id"] != str(parado["aluno_a"]) for x in r2.json()["resultados"])
    lista = (await client.get("/v1/academia/lembretes", headers=h)).json()
    c = next(x for x in lista["candidatos"] if x["aluno_id"] == str(parado["aluno_a"]))
    assert c["bloqueio"] == "enviado_recentemente"
    assert lista["historico"][0]["status"] == "simulado"


async def test_sem_consentimento_nao_recebe(client, parado, admin_sessionmaker):
    async with admin_sessionmaker() as s, s.begin():
        await s.execute(
            text("UPDATE alunos SET lembretes_whatsapp = false WHERE id = :a"),
            {"a": str(parado["aluno_a"])},
        )
    h = auth_header(_gestor(parado))
    r = await client.post("/v1/academia/lembretes/enviar", json={}, headers=h)
    assert all(x["aluno_id"] != str(parado["aluno_a"]) for x in r.json()["resultados"])
    c = next(
        x
        for x in (await client.get("/v1/academia/lembretes", headers=h)).json()["candidatos"]
        if x["aluno_id"] == str(parado["aluno_a"])
    )
    assert c["bloqueio"] == "sem_consentimento" and c["wa_link"]  # link manual continua disponível


async def test_cliente_whatsapp_monta_o_template(monkeypatch):
    visto = {}

    def handler(req: httpx.Request) -> httpx.Response:
        visto["auth"] = req.headers["authorization"]
        visto["url"] = str(req.url)
        visto["corpo"] = req.read().decode()
        return httpx.Response(200, json={"messages": [{"id": "wamid.X"}]})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        whatsapp.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )
    monkeypatch.setattr(whatsapp.settings, "whatsapp_token", "tok")
    monkeypatch.setattr(whatsapp.settings, "whatsapp_phone_number_id", "123")

    msg_id = await whatsapp.enviar_template("5511999990001", ["Ana", "4", "https://x"])
    assert msg_id == "wamid.X"
    assert visto["auth"] == "Bearer tok" and visto["url"].endswith("/123/messages")
    assert '"lembrete_sequencia"' in visto["corpo"] and '"Ana"' in visto["corpo"]

    monkeypatch.setattr(whatsapp.settings, "whatsapp_token", "")
    assert whatsapp.configurado() is False
