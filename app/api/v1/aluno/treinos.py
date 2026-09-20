from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_aluno, get_tenant_db
from app.core.redis import get_redis
from app.core.security import TokenPayload
from app.schemas.treino import (
    AjusteIn,
    AlternativaOut,
    AnuncioStubOut,
    DescansoOut,
    ExercicioConcluidoOut,
    GerarTreinoIn,
    IniciarDescansoIn,
    TreinoOut,
    TrocarIn,
)
from app.services import ads_service, treino_service, tv_events

router = APIRouter(prefix="/treinos", tags=["treinos"])


@router.post("/gerar", response_model=TreinoOut)
async def gerar_treino_rota(
    body: GerarTreinoIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> TreinoOut:
    return await treino_service.gerar_treino(
        db,
        academia_id=aluno.academia_id,
        aluno_id=aluno.aluno_id,
        minutos=body.minutos,
        foco=body.foco,
    )


@router.post("/{treino_id}/descanso", response_model=DescansoOut)
async def iniciar_descanso_rota(
    treino_id: UUID,
    body: IniciarDescansoIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> DescansoOut:
    descanso = await treino_service.registrar_descanso(
        db, academia_id=aluno.academia_id, treino_id=treino_id, ordem=body.ordem
    )
    redis = get_redis()
    ev = await ads_service.proximo_anuncio(db, redis, aluno.academia_id)
    campanha = None
    if ev:
        # Aluno em descanso: a TV troca para este anúncio agora (docs/01, passo 4).
        await tv_events.publicar(redis, aluno.academia_id, ev)
        c = ev["criativo"]
        campanha = AnuncioStubOut(
            campanha_id=ev["campanha_id"],
            marca=c["marca"],
            categoria=c["categoria"],
            desconto=c["desconto"],
            manchete=c["manchete"],
            corpo=c["corpo"],
            cupom=c["cupom"],
            qr_url=c["qr_url"],
        )
    return DescansoOut(descanso_segundos=descanso.duracao_segundos, campanha=campanha)


@router.post("/{treino_id}/exercicio/{ordem}/concluir", response_model=ExercicioConcluidoOut)
async def concluir_exercicio_rota(
    treino_id: UUID,
    ordem: int,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> ExercicioConcluidoOut:
    return await treino_service.concluir_exercicio(db, treino_id=treino_id, ordem=ordem)


@router.get("/{treino_id}", response_model=TreinoOut)
async def obter_treino_rota(
    treino_id: UUID,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> TreinoOut:
    return await treino_service.montar_treino(db, treino_id)


@router.patch("/{treino_id}/exercicio/{ordem}", response_model=TreinoOut)
async def ajustar_exercicio_rota(
    treino_id: UUID,
    ordem: int,
    body: AjusteIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> TreinoOut:
    return await treino_service.ajustar_exercicio(db, treino_id=treino_id, ordem=ordem, ajuste=body)


@router.get("/{treino_id}/exercicio/{ordem}/alternativas", response_model=list[AlternativaOut])
async def alternativas_rota(
    treino_id: UUID,
    ordem: int,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> list[AlternativaOut]:
    return await treino_service.alternativas(db, treino_id=treino_id, ordem=ordem)


@router.put("/{treino_id}/exercicio/{ordem}/trocar", response_model=TreinoOut)
async def trocar_exercicio_rota(
    treino_id: UUID,
    ordem: int,
    body: TrocarIn,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> TreinoOut:
    return await treino_service.trocar_exercicio(
        db, treino_id=treino_id, ordem=ordem, exercicio_id=body.exercicio_id
    )


@router.delete("/{treino_id}/exercicio/{ordem}", response_model=TreinoOut)
async def remover_exercicio_rota(
    treino_id: UUID,
    ordem: int,
    db: AsyncSession = Depends(get_tenant_db),
    aluno: TokenPayload = Depends(get_current_aluno),
) -> TreinoOut:
    return await treino_service.remover_exercicio(db, treino_id=treino_id, ordem=ordem)
