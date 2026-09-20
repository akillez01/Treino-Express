"""Painel do anunciante. Roda em `get_anunciante_db` (RLS por anunciante): o
anunciante enxerga só as próprias campanhas, impressões, scans, repasses e
créditos, em qualquer academia."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_anunciante
from app.core.security import TokenPayload
from app.db.tenant import get_anunciante_db

router = APIRouter(prefix="/anunciante", tags=["anunciante"])

Periodo = Literal["7d", "30d"]


def _dias(periodo: str) -> int:
    return 7 if periodo == "7d" else 30


def _rows(result) -> list[dict]:
    return [dict(r) for r in result.mappings().all()]


async def _totais(db: AsyncSession, ini: str, fim: str) -> dict:
    """Totais do período [now-ini, now-fim) em dias."""
    r = await db.execute(
        text(
            """
            SELECT COUNT(i.id)::bigint AS impressoes,
                   COALESCE(SUM(i.custo_centavos), 0)::bigint AS gasto,
                   (SELECT COUNT(*) FROM scans s JOIN impressoes i2 ON i2.id = s.impressao_id
                     WHERE i2.exibida_em >= now() - make_interval(days => :ini)
                       AND i2.exibida_em <  now() - make_interval(days => :fim))::bigint AS scans,
                   (SELECT COUNT(*) FROM scans s JOIN impressoes i2 ON i2.id = s.impressao_id
                     WHERE s.resgatado_em IS NOT NULL
                       AND i2.exibida_em >= now() - make_interval(days => :ini)
                       AND i2.exibida_em <  now() - make_interval(days => :fim))::bigint AS resgates
            FROM impressoes i
            WHERE i.exibida_em >= now() - make_interval(days => :ini)
              AND i.exibida_em <  now() - make_interval(days => :fim)
            """
        ),
        {"ini": int(ini), "fim": int(fim)},
    )
    return dict(r.mappings().one())


async def _conta(db: AsyncSession, me: str) -> dict:
    r = await db.execute(
        text("SELECT nome, saldo_centavos FROM anunciantes WHERE id = CAST(:id AS uuid)"),
        {"id": me},
    )
    row = r.mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anunciante não encontrado")
    return dict(row)


@router.get("/campanhas")
async def campanhas(
    periodo: Periodo = "7d",
    db: AsyncSession = Depends(get_anunciante_db),
    me: TokenPayload = Depends(get_current_anunciante),
):
    d = _dias(periodo)
    conta = await _conta(db, me.sub)
    atual = await _totais(db, str(d), "0")
    anterior = await _totais(db, str(2 * d), str(d))

    serie = _rows(
        await db.execute(
            text(
                """
                SELECT to_char(dia, 'YYYY-MM-DD') AS dia,
                       COALESCE(COUNT(s.id), 0)::int AS scans,
                       COALESCE(COUNT(s.id) FILTER (WHERE s.resgatado_em IS NOT NULL), 0)::int AS resgates
                FROM generate_series(date_trunc('day', now()) - make_interval(days => :d - 1),
                                     date_trunc('day', now()), interval '1 day') dia
                LEFT JOIN impressoes i ON date_trunc('day', i.exibida_em) = dia
                LEFT JOIN scans s ON s.impressao_id = i.id
                GROUP BY dia ORDER BY dia
                """
            ),
            {"d": d},
        )
    )
    lista = _rows(
        await db.execute(
            text(
                """
                SELECT c.id::text, c.nome, ac.nome AS academia, c.status::text AS status,
                       to_char(c.hora_inicio, 'HH24"h"') || '–' || to_char(c.hora_fim, 'HH24"h"') AS janela,
                       COUNT(i.id)::bigint AS impressoes,
                       COUNT(s.id)::bigint AS scans,
                       COALESCE(SUM(i.custo_centavos), 0)::bigint AS gasto
                FROM campanhas_ads c
                JOIN academias ac ON ac.id = c.academia_id
                LEFT JOIN impressoes i ON i.campanha_id = c.id
                     AND i.exibida_em >= now() - make_interval(days => :d)
                LEFT JOIN scans s ON s.impressao_id = i.id
                GROUP BY c.id, ac.nome ORDER BY c.criada_em, c.nome
                """
            ),
            {"d": d},
        )
    )
    academias = (
        await db.execute(text("SELECT COUNT(DISTINCT academia_id) FROM campanhas_ads"))
    ).scalar()
    telas = (await db.execute(text("SELECT COUNT(DISTINCT tela_id) FROM impressoes"))).scalar()
    gasto_mes = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(custo_centavos), 0) FROM impressoes "
                "WHERE exibida_em >= date_trunc('month', now())"
            )
        )
    ).scalar()
    return {
        "conta": conta,
        "periodo": periodo,
        "academias": int(academias or 0),
        "telas": int(telas or 0),
        "totais": atual,
        "anterior": anterior,
        "serie": serie,
        "campanhas": lista,
        "gasto_mes_centavos": int(gasto_mes or 0),
    }


@router.get("/metricas")
async def metricas(
    periodo: Periodo = "7d",
    db: AsyncSession = Depends(get_anunciante_db),
    me: TokenPayload = Depends(get_current_anunciante),
):
    d = _dias(periodo)
    conta = await _conta(db, me.sub)
    totais = await _totais(db, str(d), "0")
    horas = _rows(
        await db.execute(
            text(
                """
                SELECT faixa, COUNT(s.id)::int AS scans FROM (
                  VALUES ('06–09', 6, 9), ('09–12', 9, 12), ('12–15', 12, 15),
                         ('15–18', 15, 18), ('18–21', 18, 21), ('21–23', 21, 24)
                ) f(faixa, h0, h1)
                LEFT JOIN impressoes i ON extract(hour FROM i.exibida_em) >= f.h0
                     AND extract(hour FROM i.exibida_em) < f.h1
                     AND i.exibida_em >= now() - make_interval(days => :d)
                LEFT JOIN scans s ON s.impressao_id = i.id
                GROUP BY faixa ORDER BY faixa
                """
            ),
            {"d": d},
        )
    )
    criativos = _rows(
        await db.execute(
            text(
                """
                SELECT c.nome, COUNT(s.id)::int AS scans,
                       COUNT(s.id) FILTER (WHERE s.resgatado_em IS NOT NULL)::int AS resgates,
                       COALESCE(SUM(i.custo_centavos), 0)::bigint AS gasto
                FROM campanhas_ads c
                LEFT JOIN impressoes i ON i.campanha_id = c.id
                     AND i.exibida_em >= now() - make_interval(days => :d)
                LEFT JOIN scans s ON s.impressao_id = i.id
                GROUP BY c.id ORDER BY c.nome
                """
            ),
            {"d": d},
        )
    )
    academias = _rows(
        await db.execute(
            text(
                """
                SELECT ac.nome, COALESCE(ac.bairro, '') AS bairro,
                       COUNT(DISTINCT i.tela_id)::int AS telas,
                       COUNT(i.id)::bigint AS impressoes,
                       COUNT(s.id)::bigint AS scans,
                       COUNT(s.id) FILTER (WHERE s.resgatado_em IS NOT NULL)::bigint AS resgates,
                       COALESCE(SUM(i.custo_centavos), 0)::bigint AS gasto
                FROM academias ac
                JOIN campanhas_ads c ON c.academia_id = ac.id
                LEFT JOIN impressoes i ON i.campanha_id = c.id
                     AND i.exibida_em >= now() - make_interval(days => :d)
                LEFT JOIN scans s ON s.impressao_id = i.id
                GROUP BY ac.id ORDER BY ac.nome
                """
            ),
            {"d": d},
        )
    )
    return {
        "conta": conta,
        "periodo": periodo,
        "totais": totais,
        "horas": horas,
        "criativos": criativos,
        "academias": academias,
    }


@router.get("/faturamento")
async def faturamento(
    db: AsyncSession = Depends(get_anunciante_db),
    me: TokenPayload = Depends(get_current_anunciante),
):
    conta = await _conta(db, me.sub)
    mes = (
        (
            await db.execute(
                text(
                    """
                SELECT COALESCE(SUM(i.custo_centavos), 0)::bigint AS investido,
                       (SELECT COUNT(*) FROM scans s JOIN impressoes i2 ON i2.id = s.impressao_id
                         WHERE s.resgatado_em IS NOT NULL
                           AND i2.exibida_em >= date_trunc('month', now()))::bigint AS resgates
                FROM impressoes i WHERE i.exibida_em >= date_trunc('month', now())
                """
                )
            )
        )
        .mappings()
        .one()
    )
    repassado = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(liquido_centavos), 0) FROM repasses "
                "WHERE competencia = date_trunc('month', now())::date"
            )
        )
    ).scalar()
    faturas = _rows(
        await db.execute(
            text(
                """
                SELECT criado_em::date AS data, descricao, ABS(valor_centavos) AS valor_centavos,
                       COALESCE(nota_fiscal, '—') AS nota_fiscal,
                       CASE WHEN nota_fiscal IS NULL AND valor_centavos > 0 THEN 'expirado'
                            ELSE 'pago' END AS status
                FROM creditos_anunciante ORDER BY criado_em DESC
                """
            )
        )
    )
    return {
        "conta": conta,
        "investido_mes_centavos": int(mes["investido"]),
        "resgates_mes": int(mes["resgates"]),
        "repassado_centavos": int(repassado or 0),
        "faturas": faturas,
    }


class AtivaIn(BaseModel):
    ativa: bool


class CampanhaOut(BaseModel):
    id: str
    status: str


@router.patch("/campanhas/{campanha_id}", response_model=CampanhaOut)
async def alterar_campanha(
    campanha_id: uuid.UUID,
    body: AtivaIn,
    db: AsyncSession = Depends(get_anunciante_db),
    _: TokenPayload = Depends(get_current_anunciante),
):
    r = await db.execute(
        text(
            "UPDATE campanhas_ads SET status = CAST(:s AS status_campanha) "
            "WHERE id = :id AND status IN ('ativa', 'pausada') RETURNING id::text, status::text"
        ),
        {"s": "ativa" if body.ativa else "pausada", "id": str(campanha_id)},
    )
    row = r.mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campanha não encontrada")
    return CampanhaOut(**row)
