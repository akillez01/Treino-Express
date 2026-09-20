"""Painel da academia (gestor). Todas as rotas rodam na sessão tenant-scoped
(`get_tenant_db`): o RLS garante que só linhas da academia do token aparecem."""

import random
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_gestor, get_tenant_db
from app.core.redis import get_redis
from app.core.security import TokenPayload
from app.services import jukebox_player, tv_events

router = APIRouter(prefix="/academia", tags=["academia"])

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _mes(mes: str | None) -> date:
    if mes is None:
        hoje = date.today()
        return hoje.replace(day=1)
    if not MES_RE.match(mes):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "mes deve ser AAAA-MM")
    ano, m = mes.split("-")
    return date(int(ano), int(m), 1)


def _rows(result) -> list[dict]:
    return [dict(r) for r in result.mappings().all()]


async def _receita(db: AsyncSession, mes: date) -> dict[str, int]:
    r = await db.execute(
        text(
            """
            SELECT origem::text AS origem,
                   COALESCE(SUM(valor_centavos) FILTER (WHERE status = 'liquidado'), 0)::bigint AS liquidado
            FROM lancamentos WHERE competencia = :mes GROUP BY origem
            """
        ),
        {"mes": mes},
    )
    base = {"mensalidade": 0, "anuncio": 0, "jukebox": 0}
    for row in r.mappings():
        base[row["origem"]] = int(row["liquidado"])
    return base


@router.get("/resumo")
async def resumo(
    mes: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: TokenPayload = Depends(get_current_gestor),
):
    ref = _mes(mes)
    anterior = (ref.replace(day=1) - date.resolution).replace(day=1)
    prox = date(ref.year + (ref.month == 12), ref.month % 12 + 1, 1)

    tenant = (
        (await db.execute(text("SELECT nome, unidade FROM academias WHERE id = tenant_atual()")))
        .mappings()
        .first()
    )

    alunos = (
        (
            await db.execute(
                text(
                    """
                SELECT COUNT(*) FILTER (WHERE cancelado_em IS NULL) AS ativos,
                       COUNT(*) FILTER (WHERE matriculado_em >= :mes AND matriculado_em < :prox) AS novos,
                       COUNT(*) FILTER (WHERE cancelado_em IS NULL AND situacao = 'atrasado') AS atrasados
                FROM alunos
                """
                ),
                {"mes": ref, "prox": prox},
            )
        )
        .mappings()
        .one()
    )

    receita = await _receita(db, ref)
    receita_ant = await _receita(db, anterior)

    telas = _rows(
        await db.execute(
            text(
                "SELECT id::text, sala, "
                + "CASE WHEN status = 'online' AND (ultimo_heartbeat IS NULL OR ultimo_heartbeat < now() - interval '90 seconds') THEN 'offline' ELSE status::text END AS status, resolucao, ultimo_heartbeat "
                "FROM telas WHERE pareada_em IS NOT NULL ORDER BY sala"
            )
        )
    )
    fila = (
        (
            await db.execute(
                text(
                    """
                SELECT COUNT(*) AS pedidos, COALESCE(SUM(f.duracao_segundos), 0) AS segundos
                FROM jukebox_pedidos p JOIN faixas f ON f.id = p.faixa_id
                WHERE p.tocado_em IS NULL
                """
                )
            )
        )
        .mappings()
        .one()
    )
    checkins = _rows(
        await db.execute(
            text(
                """
                SELECT a.nome, a.plano::text AS plano, a.situacao::text AS situacao, c.entrada_em
                FROM check_ins c JOIN alunos a ON a.id = c.aluno_id
                ORDER BY c.entrada_em DESC LIMIT 5
                """
            )
        )
    )
    ativos = int(alunos["ativos"] or 0)
    return {
        "academia": dict(tenant) if tenant else {"nome": "Academia", "unidade": None},
        "mes": ref.strftime("%Y-%m"),
        "fechamento": (prox - date.resolution).isoformat(),
        "alunos_ativos": ativos,
        "novos_no_mes": int(alunos["novos"] or 0),
        "inadimplencia_pct": round(100 * int(alunos["atrasados"] or 0) / ativos, 1)
        if ativos
        else 0,
        "receita_centavos": receita,
        "receita_anterior_centavos": receita_ant,
        "telas": telas,
        "jukebox": {"pedidos": int(fila["pedidos"]), "segundos": int(fila["segundos"])},
        "ultimos_checkins": checkins,
    }


@router.get("/alunos")
async def alunos(
    situacao: str | None = Query(None, pattern="^(em_dia|pendente|atrasado)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_tenant_db),
    _: TokenPayload = Depends(get_current_gestor),
):
    base = """
        SELECT a.id::text, a.nome, a.email, a.plano::text AS plano, a.matriculado_em,
               a.mensalidade_centavos, a.situacao::text AS situacao,
               (SELECT COUNT(*) FROM check_ins c WHERE c.aluno_id = a.id
                  AND c.entrada_em > now() - interval '7 days') AS freq_semanal,
               (SELECT MAX(c.entrada_em) FROM check_ins c WHERE c.aluno_id = a.id) AS ultimo_checkin
        FROM alunos a WHERE a.cancelado_em IS NULL
    """
    params: dict = {"limit": limit, "offset": offset}
    if situacao:
        base += " AND a.situacao = CAST(:situacao AS situacao_pagamento)"
        params["situacao"] = situacao
    itens = _rows(
        await db.execute(text(base + " ORDER BY a.nome LIMIT :limit OFFSET :offset"), params)
    )

    contagem = (
        (
            await db.execute(
                text(
                    """
                SELECT COUNT(*) AS todos,
                       COUNT(*) FILTER (WHERE situacao = 'em_dia') AS em_dia,
                       COUNT(*) FILTER (WHERE situacao = 'pendente') AS pendente,
                       COUNT(*) FILTER (WHERE situacao = 'atrasado') AS atrasado,
                       COALESCE(AVG(mensalidade_centavos), 0)::int AS ticket
                FROM alunos WHERE cancelado_em IS NULL
                """
                )
            )
        )
        .mappings()
        .one()
    )
    freq = (
        await db.execute(
            text(
                """
                SELECT COALESCE(COUNT(*)::float / NULLIF((SELECT COUNT(*) FROM alunos WHERE cancelado_em IS NULL), 0), 0)
                FROM check_ins WHERE entrada_em > now() - interval '7 days'
                """
            )
        )
    ).scalar()
    return {
        "itens": itens,
        "contagem": dict(contagem),
        "frequencia_media": round(float(freq or 0), 1),
        "limit": limit,
        "offset": offset,
    }


@router.get("/financeiro")
async def financeiro(
    mes: str | None = None,
    db: AsyncSession = Depends(get_tenant_db),
    _: TokenPayload = Depends(get_current_gestor),
):
    ref = _mes(mes)
    receita = await _receita(db, ref)
    totais = (
        (
            await db.execute(
                text(
                    """
                SELECT COALESCE(SUM(valor_centavos) FILTER (WHERE status = 'liquidado'), 0)::bigint AS recebido,
                       COALESCE(SUM(valor_centavos) FILTER (WHERE status = 'a_receber'), 0)::bigint AS a_receber
                FROM lancamentos WHERE competencia = :mes
                """
                ),
                {"mes": ref},
            )
        )
        .mappings()
        .one()
    )
    rep = (
        (
            await db.execute(
                text(
                    """
                SELECT COALESCE(SUM(liquido_centavos), 0)::bigint AS liquido,
                       COALESCE(SUM(taxa_centavos), 0)::bigint AS taxas
                FROM repasses WHERE competencia = :mes
                """
                ),
                {"mes": ref},
            )
        )
        .mappings()
        .one()
    )
    movimentacoes = _rows(
        await db.execute(
            text(
                """
                SELECT criado_em::date AS data, descricao, origem::text AS origem,
                       valor_centavos, status::text AS status
                FROM lancamentos WHERE competencia = :mes ORDER BY criado_em DESC
                """
            ),
            {"mes": ref},
        )
    )
    repasses = _rows(
        await db.execute(
            text(
                """
                SELECT r.criado_em::date AS data, an.nome AS anunciante, r.bruto_centavos,
                       r.taxa_centavos, r.liquido_centavos, r.status::text AS status
                FROM repasses r JOIN anunciantes an ON an.id = r.anunciante_id
                WHERE r.competencia = :mes ORDER BY r.criado_em DESC
                """
            ),
            {"mes": ref},
        )
    )
    return {
        "mes": ref.strftime("%Y-%m"),
        "receita_centavos": receita,
        "recebido_centavos": int(totais["recebido"]),
        "a_receber_centavos": int(totais["a_receber"]),
        "repasse_liquido_centavos": int(rep["liquido"]),
        "taxas_centavos": int(rep["taxas"]),
        "movimentacoes": movimentacoes,
        "repasses": repasses,
    }


async def _telas(db: AsyncSession) -> list[dict]:
    return _rows(
        await db.execute(
            text(
                """
                SELECT t.id::text, t.sala, CASE WHEN t.status = 'online' AND (t.ultimo_heartbeat IS NULL OR t.ultimo_heartbeat < now() - interval '90 seconds') THEN 'offline' ELSE t.status::text END AS status, t.resolucao, t.pareada_em,
                       t.ultimo_heartbeat, t.codigo_pareamento,
                       (SELECT COUNT(*) FROM scans s JOIN impressoes i ON i.id = s.impressao_id
                         WHERE i.tela_id = t.id AND s.escaneado_em >= date_trunc('month', now())) AS qr_mes
                FROM telas t ORDER BY t.criada_em
                """
            )
        )
    )


@router.get("/telas")
async def telas(
    db: AsyncSession = Depends(get_tenant_db),
    _: TokenPayload = Depends(get_current_gestor),
):
    fila = _rows(
        await db.execute(
            text(
                """
                SELECT f.titulo, f.artista, f.duracao_segundos, a.nome AS solicitante, p.pedido_em
                FROM jukebox_pedidos p
                JOIN faixas f ON f.id = p.faixa_id JOIN alunos a ON a.id = p.aluno_id
                WHERE p.tocado_em IS NULL ORDER BY p.pedido_em
                """
            )
        )
    )
    return {"telas": await _telas(db), "fila": fila}


class Tela(BaseModel):
    id: str
    status: str


@router.post("/telas/{tela_id}/pausar", response_model=Tela)
async def pausar(
    tela_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_db),
    gestor: TokenPayload = Depends(get_current_gestor),
):
    r = await db.execute(
        text(
            """
            UPDATE telas SET status = CASE WHEN status = 'pausada' THEN 'online'::status_tela
                                           ELSE 'pausada'::status_tela END
            WHERE id = :id RETURNING id::text, status::text
            """
        ),
        {"id": str(tela_id)},
    )
    row = r.mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tela não encontrada")
    await tv_events.publicar(
        get_redis(),
        gestor.academia_id,
        {"type": "screen.pause", "tela_id": str(tela_id), "pausada": row["status"] == "pausada"},
    )
    return Tela(**row)


class Pareamento(BaseModel):
    id: str
    codigo: str


@router.post("/telas/pareamento", response_model=Pareamento, status_code=201)
async def pareamento(
    db: AsyncSession = Depends(get_tenant_db),
    _: TokenPayload = Depends(get_current_gestor),
):
    alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    codigo = "".join(random.SystemRandom().choice(alfabeto) for _ in range(6))
    codigo = f"{codigo[:3]}-{codigo[3:]}"
    r = await db.execute(
        text(
            """
            INSERT INTO telas (academia_id, sala, codigo_pareamento, status)
            VALUES (tenant_atual(), 'Nova tela', :codigo, 'offline') RETURNING id::text
            """
        ),
        {"codigo": codigo},
    )
    return Pareamento(id=r.scalar_one(), codigo=codigo)


@router.post("/jukebox/proxima", status_code=204)
async def proxima_faixa(
    db: AsyncSession = Depends(get_tenant_db),
    gestor: TokenPayload = Depends(get_current_gestor),
):
    """Pula para a próxima faixa da fila (atualiza a TV na hora)."""
    await jukebox_player.avancar(db, get_redis(), gestor.academia_id)
