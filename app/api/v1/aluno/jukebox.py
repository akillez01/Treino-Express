"""Jukebox do aluno: buscar músicas no Spotify e pedir para a TV da academia."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_aluno, get_tenant_db
from app.core.redis import get_redis
from app.core.security import TokenPayload
from app.integrations.spotify import client as spotify

router = APIRouter(prefix="/jukebox", tags=["jukebox"])

MAX_PEDIDOS_PENDENTES = 3


def _erro_spotify(exc: Exception) -> HTTPException:
    if isinstance(exc, spotify.SpotifyNaoConfigurado):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Spotify não configurado")
    return HTTPException(status.HTTP_502_BAD_GATEWAY, "Spotify indisponível no momento")


@router.get("/status")
async def situacao(_: TokenPayload = Depends(get_current_aluno)):
    return {"spotify_configurado": spotify.configurado()}


@router.get("/busca")
async def buscar(
    q: str = Query(min_length=2, max_length=100),
    limite: int = Query(10, ge=1, le=20),
    _: TokenPayload = Depends(get_current_aluno),
):
    try:
        faixas = await spotify.buscar_faixas(q, limite)
    except (spotify.SpotifyNaoConfigurado, spotify.SpotifyIndisponivel) as exc:
        raise _erro_spotify(exc) from exc
    return {"faixas": [f.dict() for f in faixas]}


class PedidoIn(BaseModel):
    spotify_id: str = Field(pattern=r"^[A-Za-z0-9]{22}$")


class PedidoOut(BaseModel):
    pedido_id: str
    titulo: str
    artista: str
    posicao: int


@router.post("/pedidos", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
async def pedir(
    body: PedidoIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    pendentes = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM jukebox_pedidos WHERE aluno_id = :aluno AND tocado_em IS NULL"
            ),
            {"aluno": str(aluno.aluno_id)},
        )
    ).scalar()
    if (pendentes or 0) >= MAX_PEDIDOS_PENDENTES:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Você já tem {MAX_PEDIDOS_PENDENTES} músicas na fila. Espere uma tocar.",
        )

    # Metadados vêm do Spotify, não do cliente: o aluno só informa o id da faixa.
    try:
        faixa = await spotify.obter_faixa(body.spotify_id)
    except (spotify.SpotifyNaoConfigurado, spotify.SpotifyIndisponivel) as exc:
        raise _erro_spotify(exc) from exc
    if faixa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faixa não encontrada no Spotify")

    faixa_id = (
        await db.execute(
            text(
                """
                INSERT INTO faixas (titulo, artista, duracao_segundos, capa_url, provedor, provedor_id)
                VALUES (:titulo, :artista, :dur, :capa, 'spotify', :pid)
                ON CONFLICT (provedor, provedor_id) WHERE provedor_id IS NOT NULL
                DO UPDATE SET titulo = EXCLUDED.titulo, artista = EXCLUDED.artista,
                              duracao_segundos = EXCLUDED.duracao_segundos, capa_url = EXCLUDED.capa_url
                RETURNING id::text
                """
            ),
            {
                "titulo": faixa.titulo,
                "artista": faixa.artista,
                "dur": faixa.duracao_segundos,
                "capa": faixa.capa_url,
                "pid": faixa.id,
            },
        )
    ).scalar_one()

    pedido_id = (
        await db.execute(
            text(
                "INSERT INTO jukebox_pedidos (academia_id, faixa_id, aluno_id) "
                "VALUES (tenant_atual(), CAST(:faixa AS uuid), CAST(:aluno AS uuid)) RETURNING id::text"
            ),
            {"faixa": faixa_id, "aluno": str(aluno.aluno_id)},
        )
    ).scalar_one()

    posicao = (
        await db.execute(text("SELECT COUNT(*) FROM jukebox_pedidos WHERE tocado_em IS NULL"))
    ).scalar()

    # Fila em tempo real (docs/05): sorted set por timestamp. Falha do Redis não
    # derruba o pedido — o Postgres é a fonte de verdade.
    try:
        await get_redis().zadd(f"jukebox:{aluno.academia_id}", {pedido_id: time.time()})
    except Exception:
        pass

    return PedidoOut(
        pedido_id=pedido_id, titulo=faixa.titulo, artista=faixa.artista, posicao=int(posicao or 1)
    )


@router.get("/fila")
async def fila(
    db: AsyncSession = Depends(get_tenant_db),
    _: TokenPayload = Depends(get_current_aluno),
):
    r = await db.execute(
        text(
            """
            SELECT p.id::text AS id, f.titulo, f.artista, f.duracao_segundos, f.capa_url,
                   split_part(a.nome, ' ', 1) AS solicitante, p.pedido_em
            FROM jukebox_pedidos p
            JOIN faixas f ON f.id = p.faixa_id JOIN alunos a ON a.id = p.aluno_id
            WHERE p.tocado_em IS NULL ORDER BY p.pedido_em
            """
        )
    )
    return {"fila": [dict(x) for x in r.mappings().all()]}
