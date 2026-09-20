from datetime import UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercicio import Exercicio
from app.models.treino import Descanso, Treino, TreinoExercicio
from app.schemas.treino import (
    AjusteIn,
    AlternativaOut,
    ExercicioConcluidoOut,
    ExercicioOut,
    TreinoOut,
)

DESCANSO_PADRAO_SEGUNDOS = 59


def calcular_qtd_exercicios(minutos: int) -> int:
    """clamp(round(minutos / 9), 3, 6) — docs/02-telas.md."""
    return min(max(round(minutos / 9), 3), 6)


async def gerar_treino(
    db: AsyncSession, *, academia_id: UUID, aluno_id: UUID, minutos: int, foco: str
) -> TreinoOut:
    qtd = calcular_qtd_exercicios(minutos)

    result = await db.execute(
        select(Exercicio)
        .where(Exercicio.foco == foco, Exercicio.ativo.is_(True))
        .order_by(Exercicio.ordem_preferencial)
        .limit(qtd)
    )
    exercicios_catalogo = list(result.scalars())
    if not exercicios_catalogo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Nenhum exercício disponível para o foco '{foco}'",
        )

    treino = Treino(
        academia_id=academia_id, aluno_id=aluno_id, minutos_disponiveis=minutos, foco=foco
    )
    db.add(treino)
    await db.flush()  # popula treino.id sem commitar (commit é feito por get_tenant_db)

    for ordem, exercicio in enumerate(exercicios_catalogo, start=1):
        db.add(
            TreinoExercicio(
                treino_id=treino.id,
                exercicio_id=exercicio.id,
                ordem=ordem,
                series=exercicio.series_padrao,
                carga=exercicio.carga_sugerida,
            )
        )
    await db.flush()
    return await montar_treino(db, treino.id)


async def montar_treino(db: AsyncSession, treino_id: UUID) -> TreinoOut:
    treino = await db.get(Treino, treino_id)
    if treino is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino não encontrado")
    rows = (
        await db.execute(
            select(TreinoExercicio, Exercicio)
            .join(Exercicio, Exercicio.id == TreinoExercicio.exercicio_id)
            .where(TreinoExercicio.treino_id == treino_id)
            .order_by(TreinoExercicio.ordem)
        )
    ).all()
    exercicios = [
        ExercicioOut(
            ordem=te.ordem,
            nome=ex.nome,
            series=te.series,
            carga=te.carga,
            imagem_url=ex.imagem_url,
            descanso_segundos=te.descanso_segundos or ex.descanso_segundos,
        )
        for te, ex in rows
    ]
    return TreinoOut(
        treino_id=treino.id,
        minutos=treino.minutos_disponiveis,
        foco=treino.foco,
        exercicios=exercicios,
        descanso_segundos=exercicios[0].descanso_segundos
        if exercicios
        else DESCANSO_PADRAO_SEGUNDOS,
    )


async def _buscar_treino_exercicio(
    db: AsyncSession, treino_id: UUID, ordem: int
) -> TreinoExercicio:
    result = await db.execute(
        select(TreinoExercicio).where(
            TreinoExercicio.treino_id == treino_id, TreinoExercicio.ordem == ordem
        )
    )
    te = result.scalar_one_or_none()
    if te is None:
        # RLS garante que treinos de outra academia nunca aparecem aqui — 404 é a
        # resposta correta tanto para "não existe" quanto para "não é seu".
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Treino ou exercício não encontrado")
    return te


async def registrar_descanso(
    db: AsyncSession, *, academia_id: UUID, treino_id: UUID, ordem: int
) -> Descanso:
    te = await _buscar_treino_exercicio(db, treino_id, ordem)
    exercicio = await db.get(Exercicio, te.exercicio_id)
    duracao = te.descanso_segundos or (
        exercicio.descanso_segundos if exercicio else DESCANSO_PADRAO_SEGUNDOS
    )

    descanso = Descanso(
        academia_id=academia_id,
        treino_exercicio_id=te.id,
        duracao_segundos=duracao,
    )
    db.add(descanso)
    await db.flush()
    return descanso


async def concluir_exercicio(
    db: AsyncSession, *, treino_id: UUID, ordem: int
) -> ExercicioConcluidoOut:
    from datetime import datetime

    te = await _buscar_treino_exercicio(db, treino_id, ordem)
    te.concluido_em = datetime.now(UTC)
    await db.flush()

    proximo = await db.execute(
        select(TreinoExercicio.ordem)
        .where(TreinoExercicio.treino_id == treino_id, TreinoExercicio.ordem > ordem)
        .order_by(TreinoExercicio.ordem)
        .limit(1)
    )
    proximo_ordem = proximo.scalar_one_or_none()

    if proximo_ordem is None:
        treino = await db.get(Treino, treino_id)
        if treino is not None:
            treino.concluido_em = datetime.now(UTC)

    return ExercicioConcluidoOut(
        ordem=ordem,
        concluido_em=te.concluido_em,
        proximo_ordem=proximo_ordem,
        treino_concluido=proximo_ordem is None,
    )


async def ajustar_exercicio(
    db: AsyncSession, *, treino_id: UUID, ordem: int, ajuste: AjusteIn
) -> TreinoOut:
    te = await _buscar_treino_exercicio(db, treino_id, ordem)
    if ajuste.series is not None:
        te.series = ajuste.series.strip()
    if ajuste.carga is not None:
        te.carga = ajuste.carga.strip() or None
    if ajuste.descanso_segundos is not None:
        if ajuste.aplicar_descanso_a_todos:
            await db.execute(
                update(TreinoExercicio)
                .where(TreinoExercicio.treino_id == treino_id)
                .values(descanso_segundos=ajuste.descanso_segundos)
            )
        else:
            te.descanso_segundos = ajuste.descanso_segundos
    await db.flush()
    return await montar_treino(db, treino_id)


async def alternativas(db: AsyncSession, *, treino_id: UUID, ordem: int) -> list[AlternativaOut]:
    """Exercícios do mesmo foco que ainda não estão neste treino."""
    await _buscar_treino_exercicio(db, treino_id, ordem)
    treino = await db.get(Treino, treino_id)
    no_treino = select(TreinoExercicio.exercicio_id).where(TreinoExercicio.treino_id == treino_id)
    rows = (
        await db.execute(
            select(Exercicio)
            .where(
                Exercicio.foco == treino.foco,
                Exercicio.ativo.is_(True),
                Exercicio.id.not_in(no_treino),
            )
            .order_by(Exercicio.ordem_preferencial, Exercicio.nome)
        )
    ).scalars()
    return [
        AlternativaOut(
            exercicio_id=e.id,
            nome=e.nome,
            series=e.series_padrao,
            carga=e.carga_sugerida,
            imagem_url=e.imagem_url,
            descanso_segundos=e.descanso_segundos,
        )
        for e in rows
    ]


async def trocar_exercicio(
    db: AsyncSession, *, treino_id: UUID, ordem: int, exercicio_id: UUID
) -> TreinoOut:
    te = await _buscar_treino_exercicio(db, treino_id, ordem)
    treino = await db.get(Treino, treino_id)
    novo = await db.get(Exercicio, exercicio_id)  # RLS: só catálogo global ou da academia
    if novo is None or not novo.ativo or novo.foco != treino.foco:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Exercício inválido para este foco"
        )
    repetido = await db.execute(
        select(TreinoExercicio.id).where(
            TreinoExercicio.treino_id == treino_id, TreinoExercicio.exercicio_id == exercicio_id
        )
    )
    if repetido.first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este exercício já está no treino")
    te.exercicio_id = novo.id
    te.series = novo.series_padrao
    te.carga = novo.carga_sugerida
    te.descanso_segundos = None
    te.concluido_em = None
    await db.flush()
    return await montar_treino(db, treino_id)


async def remover_exercicio(db: AsyncSession, *, treino_id: UUID, ordem: int) -> TreinoOut:
    te = await _buscar_treino_exercicio(db, treino_id, ordem)
    total = (
        await db.execute(
            select(func.count())
            .select_from(TreinoExercicio)
            .where(TreinoExercicio.treino_id == treino_id)
        )
    ).scalar()
    if (total or 0) <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "O treino precisa ter ao menos um exercício")
    # descansos ligados a este exercício saem junto (ON DELETE CASCADE)
    await db.delete(te)
    await db.flush()
    return await montar_treino(db, treino_id)
