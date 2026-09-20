"""Gateway WebSocket da TV (docs/05-api-e-websocket.md).

`WSS /ws/tv/{academia_id}?token=<jwt_da_tela>`: uma sala por academia, uma
conexão por tela. O token é o JWT do tipo `tela` emitido no pareamento; ele
precisa ser da academia do caminho, então uma tela nunca recebe eventos de
outra unidade, mesmo com token válido.

Servidor -> tela: tv.info, ad.show, jukebox.now, jukebox.queue, screen.pause, ping
Tela -> servidor: pong, ad.impression (só conta quando a tela confirma)
"""

import asyncio
import contextlib
import json
import time
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import text

from app.core.redis import get_redis
from app.core.security import InvalidTokenError, decode_access_token
from app.db.tenant import tenant_session
from app.services import ads_service, jukebox_player, tv_events

router = APIRouter()

HEARTBEAT_S = 30
PONG_TIMEOUT_S = 60
TICK_S = 1
JUKEBOX_TICK_S = 2
SEM_ANUNCIO_S = 10


@router.websocket("/ws/tv/{academia_id}")
async def tv_socket(ws: WebSocket, academia_id: uuid.UUID, token: str = Query(...)):
    try:
        claims = decode_access_token(token)
    except InvalidTokenError:
        await ws.close(code=4401)
        return
    if claims.type != "tela" or claims.academia_id != academia_id:
        await ws.close(code=4403)
        return
    tela_id = claims.sub
    academia = str(academia_id)
    redis = get_redis()

    async with tenant_session(academia) as db:
        info = (
            (
                await db.execute(
                    text(
                        "SELECT t.sala, t.status::text AS status, a.nome, a.unidade "
                        "FROM telas t JOIN academias a ON a.id = t.academia_id "
                        "WHERE t.id = CAST(:id AS uuid)"
                    ),
                    {"id": tela_id},
                )
            )
            .mappings()
            .first()
        )
    if info is None:
        await ws.close(code=4404)
        return

    await ws.accept()
    estado = {"pausada": info["status"] == "pausada", "pong": time.monotonic(), "prox_anuncio": 0.0}

    async def enviar(evento: dict) -> None:
        await ws.send_text(json.dumps(evento, default=str))

    async def batida() -> None:
        async with tenant_session(academia) as db:
            await db.execute(
                text(
                    "UPDATE telas SET ultimo_heartbeat = now(), status = "
                    "CASE WHEN status = 'pausada' THEN status ELSE 'online' END "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": tela_id},
            )
        await redis.set(f"tv:online:{academia}:{tela_id}", "1", ex=PONG_TIMEOUT_S)

    async def snapshot() -> None:
        await enviar(
            {
                "type": "tv.info",
                "academia": {"nome": info["nome"], "unidade": info["unidade"]},
                "sala": info["sala"],
            }
        )
        await enviar({"type": "screen.pause", "pausada": estado["pausada"]})
        await enviar(await jukebox_player.evento_agora(redis, academia))
        async with tenant_session(academia) as db:
            await enviar(await jukebox_player.evento_fila(db))

    async def ler() -> None:
        while True:
            try:
                msg = json.loads(await ws.receive_text())
            except json.JSONDecodeError:
                continue
            tipo = msg.get("type")
            if tipo == "pong":
                estado["pong"] = time.monotonic()
                await batida()
            elif tipo == "ad.impression":
                camp, nonce = str(msg.get("campanha_id", "")), str(msg.get("nonce", ""))
                if not camp or not nonce:
                    continue
                try:
                    async with tenant_session(academia) as db:
                        await ads_service.registrar_impressao(
                            db, redis, tela_id=tela_id, campanha_id=camp, nonce=nonce
                        )
                except Exception:
                    continue  # id malformado ou campanha inexistente: ignora

    async def encaminhar() -> None:
        try:
            async for m in pubsub.listen():
                if m["type"] != "message":
                    continue
                ev = json.loads(m["data"])
                if ev.get("tela_id") not in (None, tela_id):
                    continue
                if ev.get("type") == "screen.pause":
                    estado["pausada"] = bool(ev.get("pausada"))
                await enviar(ev)
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe()
                await pubsub.aclose()

    async def relogio() -> None:
        ultimo_ping = 0.0
        ultimo_juke = 0.0
        while True:
            await asyncio.sleep(TICK_S)
            agora = time.monotonic()
            if agora - estado["pong"] > PONG_TIMEOUT_S:
                return  # sem resposta: a tela é considerada offline
            if agora - ultimo_ping >= HEARTBEAT_S:
                ultimo_ping = agora
                await enviar({"type": "ping"})
            if agora - ultimo_juke >= JUKEBOX_TICK_S:
                ultimo_juke = agora
                async with tenant_session(academia) as db:
                    await jukebox_player.tick(db, redis, academia)
            if not estado["pausada"] and agora >= estado["prox_anuncio"]:
                async with tenant_session(academia) as db:
                    ev = await ads_service.proximo_anuncio(db, redis, academia)
                if ev:
                    estado["prox_anuncio"] = agora + ev["duracao_s"]
                    await enviar(ev)
                else:
                    estado["prox_anuncio"] = agora + SEM_ANUNCIO_S

    tarefas: set[asyncio.Task] = set()
    # Assina o canal ANTES do snapshot: um evento publicado entre os dois se perderia
    # (pub/sub não guarda histórico), e o snapshot já reflete o estado do banco.
    pubsub = redis.pubsub()
    await pubsub.subscribe(tv_events.canal(academia))
    try:
        await batida()
        await snapshot()
        tarefas = {asyncio.create_task(f()) for f in (ler, encaminhar, relogio)}
        await asyncio.wait(tarefas, return_when=asyncio.FIRST_COMPLETED)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        for t in tarefas:
            t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.gather(*tarefas, return_exceptions=True)
        with contextlib.suppress(Exception):
            async with tenant_session(academia) as db:
                await db.execute(
                    text(
                        "UPDATE telas SET status = CASE WHEN status = 'pausada' THEN status "
                        "ELSE 'offline' END WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": tela_id},
                )
            await redis.delete(f"tv:online:{academia}:{tela_id}")
        with contextlib.suppress(Exception):
            await pubsub.aclose()
        with contextlib.suppress(Exception):
            await ws.close()
