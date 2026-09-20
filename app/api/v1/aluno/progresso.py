"""Desempenho e evolução do aluno."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_aluno, get_tenant_db
from app.core.security import TokenPayload
from app.integrations.whatsapp import client as whatsapp
from app.services import progresso_service, ranking_service

router = APIRouter(tags=["progresso"])


@router.get("/progresso")
async def meu_progresso(
    dias: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    return await progresso_service.progresso(db, aluno.aluno_id, dias)


class MetaIn(BaseModel):
    meta_semanal: int = Field(ge=1, le=7)


@router.put("/progresso/meta")
async def definir_meta(
    body: MetaIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    await db.execute(
        text("UPDATE alunos SET meta_semanal = :m WHERE id = CAST(:a AS uuid)"),
        {"m": body.meta_semanal, "a": str(aluno.aluno_id)},
    )
    return {"meta_semanal": body.meta_semanal}


@router.get("/treinos/{treino_id}/resumo")
async def resumo(
    treino_id: UUID,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    r = await progresso_service.resumo_treino(db, aluno.aluno_id, treino_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado")
    return r


class EsforcoIn(BaseModel):
    esforco: int = Field(ge=1, le=5)


@router.post("/treinos/{treino_id}/avaliar", status_code=status.HTTP_204_NO_CONTENT)
async def avaliar(
    treino_id: UUID,
    body: EsforcoIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    r = await db.execute(
        text(
            "UPDATE treinos SET esforco = :e WHERE id = CAST(:t AS uuid) "
            "AND aluno_id = CAST(:a AS uuid) RETURNING id"
        ),
        {"e": body.esforco, "t": str(treino_id), "a": str(aluno.aluno_id)},
    )
    if r.first() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado")


class MetaExercicioIn(BaseModel):
    exercicio: str = Field(min_length=2, max_length=80)
    alvo_kg: float = Field(gt=0, le=1000)
    prazo: date | None = None


@router.put("/progresso/metas")
async def definir_meta_exercicio(
    body: MetaExercicioIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    if body.prazo and body.prazo < date.today():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "O prazo não pode estar no passado"
        )
    await db.execute(
        text(
            """
            INSERT INTO metas_exercicio (academia_id, aluno_id, exercicio, alvo_kg, prazo)
            VALUES (tenant_atual(), CAST(:a AS uuid), :e, :k, :p)
            ON CONFLICT (aluno_id, exercicio)
            DO UPDATE SET alvo_kg = EXCLUDED.alvo_kg, prazo = EXCLUDED.prazo, atingida_em = NULL
            """
        ),
        {"a": str(aluno.aluno_id), "e": body.exercicio.strip(), "k": body.alvo_kg, "p": body.prazo},
    )
    return {"ok": True}


@router.delete("/progresso/metas", status_code=status.HTTP_204_NO_CONTENT)
async def remover_meta_exercicio(
    exercicio: str = Query(min_length=2, max_length=80),
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    await db.execute(
        text("DELETE FROM metas_exercicio WHERE aluno_id = CAST(:a AS uuid) AND exercicio = :e"),
        {"a": str(aluno.aluno_id), "e": exercicio},
    )


class PreferenciasIn(BaseModel):
    ranking_visivel: bool | None = None
    lembretes_whatsapp: bool | None = None
    telefone: str | None = Field(default=None, max_length=25)


@router.get("/aluno/preferencias")
async def preferencias(
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    r = (
        (
            await db.execute(
                text(
                    "SELECT ranking_visivel, lembretes_whatsapp, telefone FROM alunos "
                    "WHERE id = CAST(:a AS uuid)"
                ),
                {"a": str(aluno.aluno_id)},
            )
        )
        .mappings()
        .one()
    )
    return dict(r)


@router.put("/aluno/preferencias")
async def salvar_preferencias(
    body: PreferenciasIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    atual = await preferencias(db, aluno)
    telefone = atual["telefone"]
    if body.telefone is not None:
        if body.telefone.strip() == "":
            telefone = None
        else:
            telefone = whatsapp.normalizar_telefone(body.telefone)
            if telefone is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT, "Telefone inválido. Use DDD + número."
                )
    lembretes = (
        atual["lembretes_whatsapp"] if body.lembretes_whatsapp is None else body.lembretes_whatsapp
    )
    if lembretes and not telefone:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Informe seu telefone para receber lembretes."
        )
    ranking = atual["ranking_visivel"] if body.ranking_visivel is None else body.ranking_visivel
    await db.execute(
        text(
            "UPDATE alunos SET ranking_visivel = :r, lembretes_whatsapp = :l, telefone = :t "
            "WHERE id = CAST(:a AS uuid)"
        ),
        {"r": ranking, "l": lembretes, "t": telefone, "a": str(aluno.aluno_id)},
    )
    return {"ranking_visivel": ranking, "lembretes_whatsapp": lembretes, "telefone": telefone}


@router.get("/ranking")
async def ranking(
    metrica: str = Query("treinos", pattern="^(treinos|volume|sequencia)$"),
    dias: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
):
    return await ranking_service.ranking(db, aluno.aluno_id, metrica, dias)
