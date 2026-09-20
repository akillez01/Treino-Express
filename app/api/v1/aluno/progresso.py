"""Desempenho e evolução do aluno."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_aluno, get_tenant_db
from app.core.security import TokenPayload
from app.services import progresso_service

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
