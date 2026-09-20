"""Jukebox do aluno: buscar músicas no Spotify e pedir para a TV da academia."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_aluno, get_tenant_db
from app.core.redis import get_redis
from app.core.security import TokenPayload
from app.integrations.spotify import client as spotify
from app.services import jukebox_player, tv_events

router = APIRouter(prefix="/jukebox", tags=["jukebox"])

MAX_PEDIDOS_PENDENTES = 3
SPOTIFY_ID_PATTERN = r"^[A-Za-z0-9]{22}$"


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
    spotify_id: str = Field(pattern=SPOTIFY_ID_PATTERN)


class PedidoOut(BaseModel):
    pedido_id: str
    titulo: str
    artista: str
    posicao: int


class BibliotecaFaixaOut(BaseModel):
    spotify_id: str
    titulo: str
    artista: str
    duracao_segundos: int
    capa_url: str | None
    adicionada_em: datetime


class BibliotecaFaixaIn(BaseModel):
    spotify_id: str = Field(pattern=SPOTIFY_ID_PATTERN)


@router.get("/biblioteca")
async def listar_biblioteca(
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    resultado = await db.execute(
        text(
            """
            SELECT spotify_id, titulo, artista, duracao_segundos, capa_url, adicionada_em
            FROM aluno_biblioteca_faixas
            WHERE aluno_id = CAST(:aluno AS uuid)
            ORDER BY adicionada_em DESC
            """
        ),
        {"aluno": str(aluno.aluno_id)},
    )
    return {"faixas": [BibliotecaFaixaOut(**dict(row)) for row in resultado.mappings().all()]}


@router.post("/biblioteca", response_model=BibliotecaFaixaOut, status_code=status.HTTP_201_CREATED)
async def salvar_na_biblioteca(
    body: BibliotecaFaixaIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    try:
        faixa = await spotify.obter_faixa(body.spotify_id)
    except (spotify.SpotifyNaoConfigurado, spotify.SpotifyIndisponivel) as exc:
        raise _erro_spotify(exc) from exc
    if faixa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faixa não encontrada no Spotify")

    resultado = await db.execute(
        text(
            """
            INSERT INTO aluno_biblioteca_faixas
                (aluno_id, spotify_id, titulo, artista, duracao_segundos, capa_url)
            VALUES
                (CAST(:aluno AS uuid), :spotify_id, :titulo, :artista, :duracao, :capa)
            ON CONFLICT (aluno_id, spotify_id) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                artista = EXCLUDED.artista,
                duracao_segundos = EXCLUDED.duracao_segundos,
                capa_url = EXCLUDED.capa_url,
                adicionada_em = now()
            RETURNING spotify_id, titulo, artista, duracao_segundos, capa_url, adicionada_em
            """
        ),
        {
            "aluno": str(aluno.aluno_id),
            "spotify_id": faixa.id,
            "titulo": faixa.titulo,
            "artista": faixa.artista,
            "duracao": faixa.duracao_segundos,
            "capa": faixa.capa_url,
        },
    )
    return BibliotecaFaixaOut(**dict(resultado.mappings().one()))


@router.delete("/biblioteca/{spotify_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_da_biblioteca(
    spotify_id: str = Path(pattern=SPOTIFY_ID_PATTERN),
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    resultado = await db.execute(
        text(
            """
            DELETE FROM aluno_biblioteca_faixas
            WHERE aluno_id = CAST(:aluno AS uuid) AND spotify_id = :spotify_id
            """
        ),
        {"aluno": str(aluno.aluno_id), "spotify_id": spotify_id},
    )
    if resultado.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Faixa não está na sua biblioteca")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        redis = get_redis()
        await redis.zadd(f"jukebox:{aluno.academia_id}", {pedido_id: time.time()})
        await tv_events.publicar(redis, aluno.academia_id, await jukebox_player.evento_fila(db))
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
