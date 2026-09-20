"""Estado "tocando agora" da jukebox de cada academia.

O sistema não toca áudio (sai do som da academia): ele controla a ordem. Uma
faixa "toca" desde o instante em que é escolhida até durar `duracao_s`; então a
próxima da fila assume. O estado atual vive num hash Redis
(`jukebox:now:{academia_id}`); a fila é a tabela `jukebox_pedidos` (tocado_em
NULL = ainda na fila; preenchido no instante em que a faixa começa).
"""

import time

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import tv_events

LOCK_TTL_S = 5
FILA_VISIVEL = 8


def _now_key(academia_id) -> str:
    return f"jukebox:now:{academia_id}"


def _mmss(segundos: int) -> str:
    return f"{segundos // 60}:{segundos % 60:02d}"


async def evento_fila(db: AsyncSession) -> dict:
    rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT f.titulo, f.artista, f.duracao_segundos, f.capa_url,
                           split_part(a.nome, ' ', 1) AS solicitante
                    FROM jukebox_pedidos p
                    JOIN faixas f ON f.id = p.faixa_id JOIN alunos a ON a.id = p.aluno_id
                    WHERE p.tocado_em IS NULL ORDER BY p.pedido_em LIMIT :n
                    """
                ),
                {"n": FILA_VISIVEL},
            )
        )
        .mappings()
        .all()
    )
    total = (
        await db.execute(text("SELECT COUNT(*) FROM jukebox_pedidos WHERE tocado_em IS NULL"))
    ).scalar()
    return {
        "type": "jukebox.queue",
        "total": int(total or 0),
        "fila": [
            {
                "titulo": r["titulo"],
                "artista": r["artista"],
                "pedida_por": r["solicitante"],
                "duracao": _mmss(r["duracao_segundos"]),
                "capa_url": r["capa_url"],
            }
            for r in rows
        ],
    }


async def evento_agora(redis: Redis, academia_id) -> dict:
    h = await redis.hgetall(_now_key(academia_id))
    if not h:
        return {"type": "jukebox.now", "faixa": None}
    return {
        "type": "jukebox.now",
        "faixa": {
            "titulo": h["titulo"],
            "artista": h["artista"],
            "duracao_s": int(h["duracao_s"]),
            "posicao_s": max(0, int(time.time() - float(h["started_at"]))),
            "pedida_por": h["pedida_por"],
            "capa_url": h.get("capa_url") or None,
        },
    }


async def avancar(db: AsyncSession, redis: Redis, academia_id, *, publicar: bool = True) -> bool:
    """Passa para a próxima faixa da fila (ou zera o "tocando agora" se a fila
    acabou). Idempotente entre telas: um lock curto evita avanços duplicados."""
    if not await redis.set(f"jukebox:lock:{academia_id}", "1", nx=True, ex=LOCK_TTL_S):
        return False
    proxima = (
        (
            await db.execute(
                text(
                    """
                    UPDATE jukebox_pedidos SET tocado_em = now()
                    WHERE id = (SELECT id FROM jukebox_pedidos WHERE tocado_em IS NULL
                                ORDER BY pedido_em LIMIT 1)
                    RETURNING id::text, faixa_id, aluno_id
                    """
                )
            )
        )
        .mappings()
        .first()
    )
    chave = _now_key(academia_id)
    if proxima is None:
        await redis.delete(chave)
    else:
        f = (
            (
                await db.execute(
                    text(
                        "SELECT f.titulo, f.artista, f.duracao_segundos, f.capa_url, "
                        "split_part(a.nome, ' ', 1) AS solicitante "
                        "FROM faixas f, alunos a WHERE f.id = :f AND a.id = :a"
                    ),
                    {"f": proxima["faixa_id"], "a": proxima["aluno_id"]},
                )
            )
            .mappings()
            .one()
        )
        await redis.hset(
            chave,
            mapping={
                "pedido_id": proxima["id"],
                "titulo": f["titulo"],
                "artista": f["artista"],
                "duracao_s": f["duracao_segundos"],
                "capa_url": f["capa_url"] or "",
                "pedida_por": f["solicitante"],
                "started_at": time.time(),
            },
        )
    if publicar:
        await tv_events.publicar(redis, academia_id, await evento_agora(redis, academia_id))
        await tv_events.publicar(redis, academia_id, await evento_fila(db))
    return True


async def tick(db: AsyncSession, redis: Redis, academia_id) -> bool:
    """Chamado periodicamente pelo gateway: troca a faixa quando ela acaba (ou
    inicia a primeira se ninguém estiver tocando e houver fila)."""
    h = await redis.hgetall(_now_key(academia_id))
    if h and time.time() - float(h["started_at"]) < int(h["duracao_s"]):
        return False
    if not h:
        tem_fila = (
            await db.execute(text("SELECT 1 FROM jukebox_pedidos WHERE tocado_em IS NULL LIMIT 1"))
        ).first()
        if not tem_fila:
            return False
    return await avancar(db, redis, academia_id)
