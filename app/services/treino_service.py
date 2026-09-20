from datetime import UTC
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercicio import Exercicio
from app.models.treino import Descanso, Treino, TreinoExercicio
from app.schemas.treino import ExercicioConcluidoOut, ExercicioOut, TreinoOut

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
    await (
        db.flush()
    )  # popula treino.id sem commitar (commit é feito por get_tenant_db no fim do request)

    treino_exercicios: list[TreinoExercicio] = []
    for ordem, exercicio in enumerate(exercicios_catalogo, start=1):
        te = TreinoExercicio(
            treino_id=treino.id,
            exercicio_id=exercicio.id,
            ordem=ordem,
            series=exercicio.series_padrao,
            carga=exercicio.carga_sugerida,
        )
        db.add(te)
        treino_exercicios.append(te)
    await db.flush()

    return TreinoOut(
        treino_id=treino.id,
        minutos=minutos,
        foco=foco,
        exercicios=[
            ExercicioOut(ordem=te.ordem, nome=ex.nome, series=te.series, carga=te.carga)
            for te, ex in zip(treino_exercicios, exercicios_catalogo, strict=True)
        ],
        descanso_segundos=exercicios_catalogo[0].descanso_segundos or DESCANSO_PADRAO_SEGUNDOS,
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
    duracao = exercicio.descanso_segundos if exercicio else DESCANSO_PADRAO_SEGUNDOS

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
