"""Gateway WebSocket da TV, pareamento e QR.

O WebSocket roda contra um servidor uvicorn real em outro processo: o TestClient
do Starlette usa um event loop próprio e não conviveria com o pool asyncpg
compartilhado da suíte."""

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid

import httpx
import pytest
import websockets
from sqlalchemy import text

from app.core.security import create_access_token
from tests.conftest import PROJECT_ROOT, auth_header

PORT = 8765
HTTP = f"http://127.0.0.1:{PORT}"
WS = f"ws://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def servidor():
    env = {**os.environ, "PUBLIC_API_URL": HTTP}
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(PORT),
            "--log-level",
            "warning",
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )
    for _ in range(50):
        try:
            if httpx.get(f"{HTTP}/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        proc.kill()
        pytest.fail("servidor de teste não subiu")
    yield
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
async def tela(admin_sessionmaker, duas_academias):
    """Uma tela e uma campanha sempre elegível na academia A."""
    a = str(duas_academias["academia_a"])
    ids = {k: str(uuid.uuid4()) for k in ("tela", "anun", "camp")}
    async with admin_sessionmaker() as s, s.begin():
        await s.execute(
            text(
                "INSERT INTO telas (id, academia_id, sala, status, pareada_em) "
                "VALUES (:id, :a, 'Sala TV', 'offline', now())"
            ),
            {"id": ids["tela"], "a": a},
        )
        await s.execute(
            text("INSERT INTO anunciantes (id, nome, email_contato) VALUES (:id, 'Marca TV', :e)"),
            {"id": ids["anun"], "e": f"{ids['anun'][:8]}@x.com"},
        )
        await s.execute(
            text(
                """INSERT INTO campanhas_ads (id, anunciante_id, academia_id, nome, desconto_rotulo,
                   manchete, corpo, cupom, status, inicio, hora_inicio, hora_fim,
                   orcamento_centavos, cpm_centavos)
                   VALUES (:c, :an, :a, 'Camp TV', '10%', 'm', 'c', 'TV10', 'ativa',
                   CURRENT_DATE - 1, '00:00', '23:59', 100000, 100000)"""
            ),
            {"c": ids["camp"], "an": ids["anun"], "a": a},
        )
    token = create_access_token(
        subject=ids["tela"], type="tela", academia_id=duas_academias["academia_a"]
    )
    return {**ids, "token": token, "academia": a}


async def _receber(ws, tipo, limite=8):
    fim = asyncio.get_event_loop().time() + limite
    while asyncio.get_event_loop().time() < fim:
        ev = json.loads(await asyncio.wait_for(ws.recv(), limite))
        if ev["type"] == "ping":
            await ws.send(json.dumps({"type": "pong"}))
        if ev["type"] == tipo:
            return ev
    pytest.fail(f"evento {tipo} não chegou")


async def _contar_impressoes(admin_sessionmaker, campanha):
    async with admin_sessionmaker() as s:
        return (
            await s.execute(
                text("SELECT COUNT(*) FROM impressoes WHERE campanha_id = :c"), {"c": campanha}
            )
        ).scalar()


async def test_snapshot_anuncio_e_impressao(servidor, tela, admin_sessionmaker):
    url = f"{WS}/ws/tv/{tela['academia']}?token={tela['token']}"
    async with websockets.connect(url) as ws:
        info = await _receber(ws, "tv.info")
        assert info["sala"] == "Sala TV"
        ad = await _receber(ws, "ad.show")
        assert ad["campanha_id"] == tela["camp"]
        assert ad["criativo"]["qr_url"].endswith(f"/r/{tela['camp']}/{ad['nonce']}")

        imp = json.dumps(
            {"type": "ad.impression", "campanha_id": ad["campanha_id"], "nonce": ad["nonce"]}
        )
        falso = json.dumps(
            {"type": "ad.impression", "campanha_id": ad["campanha_id"], "nonce": "inventado1"}
        )
        await ws.send(imp)
        await ws.send(imp)  # repetida: não conta de novo
        await ws.send(falso)  # nonce que não emitimos: ignorada
        await asyncio.sleep(1)
        assert await _contar_impressoes(admin_sessionmaker, tela["camp"]) == 1

    # QR: primeiro scan registra, o repetido não duplica
    qr = ad["criativo"]["qr_url"]
    r1 = httpx.get(qr, follow_redirects=False)
    r2 = httpx.get(qr, follow_redirects=False)
    assert r1.status_code == 302 and "cupom=TV10" in r1.headers["location"]
    assert r2.status_code == 302
    async with admin_sessionmaker() as s:
        n = (
            await s.execute(
                text(
                    "SELECT COUNT(*) FROM scans sc JOIN impressoes i ON i.id = sc.impressao_id "
                    "WHERE i.campanha_id = :c"
                ),
                {"c": tela["camp"]},
            )
        ).scalar()
    assert n == 1

    # a tela fica offline ao desconectar
    await asyncio.sleep(0.5)
    async with admin_sessionmaker() as s:
        st = (
            await s.execute(
                text("SELECT status::text FROM telas WHERE id = :i"), {"i": tela["tela"]}
            )
        ).scalar()
    assert st == "offline"


async def test_rejeita_token_invalido_e_outra_academia(servidor, tela, duas_academias):
    for url in (
        f"{WS}/ws/tv/{tela['academia']}?token=abc",
        f"{WS}/ws/tv/{duas_academias['academia_b']}?token={tela['token']}",
    ):
        with pytest.raises(websockets.exceptions.InvalidStatus):
            async with websockets.connect(url) as ws:
                await ws.recv()


async def test_token_de_aluno_nao_abre_ws_de_tv(servidor, duas_academias):
    url = f"{WS}/ws/tv/{duas_academias['academia_a']}?token={duas_academias['token_a']}"
    with pytest.raises(websockets.exceptions.InvalidStatus):
        async with websockets.connect(url) as ws:
            await ws.recv()


async def test_pausar_avisa_a_tela(servidor, tela, duas_academias, client):
    gestor = create_access_token(
        subject=tela["academia"], type="gestor", academia_id=duas_academias["academia_a"]
    )
    async with websockets.connect(f"{WS}/ws/tv/{tela['academia']}?token={tela['token']}") as ws:
        await _receber(ws, "tv.info")
        r = await client.post(
            f"/v1/academia/telas/{tela['tela']}/pausar", headers=auth_header(gestor)
        )
        assert r.status_code == 200
        ev = await _receber(ws, "screen.pause")
        while ev["pausada"] is not True:  # ignora o snapshot inicial (pausada=False)
            ev = await _receber(ws, "screen.pause")
        assert ev["pausada"] is True


async def test_pareamento_com_codigo_de_uso_unico(client, duas_academias):
    gestor = create_access_token(
        subject=str(duas_academias["academia_a"]),
        type="gestor",
        academia_id=duas_academias["academia_a"],
    )
    r = await client.post("/v1/academia/telas/pareamento", headers=auth_header(gestor))
    codigo = r.json()["codigo"]

    ok = await client.post("/v1/tv/parear", json={"codigo": codigo})
    assert ok.status_code == 200
    assert ok.json()["academia_id"] == str(duas_academias["academia_a"])

    de_novo = await client.post("/v1/tv/parear", json={"codigo": codigo})
    assert de_novo.status_code == 404


async def test_avanca_fila_da_jukebox(admin_sessionmaker, duas_academias):
    from app.core.redis import get_redis
    from app.db.tenant import tenant_session
    from app.services import jukebox_player

    a, aluno = str(duas_academias["academia_a"]), str(duas_academias["aluno_a"])
    async with admin_sessionmaker() as s, s.begin():
        for i in (1, 2):
            f = (
                await s.execute(
                    text(
                        "INSERT INTO faixas (titulo, artista, duracao_segundos) "
                        "VALUES (:t, 'X', 100) RETURNING id::text"
                    ),
                    {"t": f"Faixa {i}"},
                )
            ).scalar()
            await s.execute(
                text(
                    "INSERT INTO jukebox_pedidos (academia_id, faixa_id, aluno_id, pedido_em) "
                    "VALUES (:a, CAST(:f AS uuid), :al, now() + make_interval(secs => :i))"
                ),
                {"a": a, "f": f, "al": aluno, "i": i},
            )
    redis = get_redis()
    await redis.delete(f"jukebox:now:{a}", f"jukebox:lock:{a}")

    async with tenant_session(a) as db:
        assert await jukebox_player.avancar(db, redis, a, publicar=False)
    assert (await jukebox_player.evento_agora(redis, a))["faixa"]["titulo"] == "Faixa 1"

    await redis.delete(f"jukebox:lock:{a}")
    async with tenant_session(a) as db:
        await jukebox_player.avancar(db, redis, a, publicar=False)
        fila = await jukebox_player.evento_fila(db)
    assert (await jukebox_player.evento_agora(redis, a))["faixa"]["titulo"] == "Faixa 2"
    assert fila["total"] == 0
