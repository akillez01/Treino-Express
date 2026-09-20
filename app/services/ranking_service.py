"""Ranking da academia (opt-in): compara só quem escolheu participar.

Mostra apenas primeiro nome + inicial do sobrenome. O RLS já limita a consulta
à academia do aluno, então ninguém vê alunos de outra unidade."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.progresso_service import TZ, _sequencias

METRICAS = ("treinos", "volume", "sequencia")


def nome_publico(nome: str) -> str:
    partes = nome.split()
    if len(partes) < 2:
        return partes[0] if partes else "Aluno"
    return f"{partes[0]} {partes[-1][0]}."


async def ranking(db: AsyncSession, aluno_id: UUID, metrica: str, dias: int = 30) -> dict:
    meu = (
        await db.execute(
            text("SELECT ranking_visivel FROM alunos WHERE id = CAST(:a AS uuid)"),
            {"a": str(aluno_id)},
        )
    ).scalar()
    if not meu:
        return {"participando": False, "metrica": metrica, "itens": [], "total": 0, "eu": None}

    agora = datetime.now(TZ)
    desde = agora - timedelta(days=dias)
    alunos = (
        (
            await db.execute(
                text(
                    """
                    SELECT a.id::text AS id, a.nome,
                           COUNT(t.id) FILTER (WHERE t.concluido_em >= :desde) AS treinos,
                           COALESCE(SUM(t.volume_kg) FILTER (WHERE t.concluido_em >= :desde), 0)::float AS volume
                    FROM alunos a
                    LEFT JOIN treinos t ON t.aluno_id = a.id AND t.concluido_em IS NOT NULL
                    WHERE a.ranking_visivel AND a.cancelado_em IS NULL
                    GROUP BY a.id
                    """
                ),
                {"desde": desde},
            )
        )
        .mappings()
        .all()
    )
    datas: dict[str, set] = {}
    for aid, d in (
        await db.execute(
            text(
                "SELECT t.aluno_id::text, (t.concluido_em AT TIME ZONE 'America/Sao_Paulo')::date "
                "FROM treinos t JOIN alunos a ON a.id = t.aluno_id "
                "WHERE a.ranking_visivel AND t.concluido_em >= :d"
            ),
            {"d": agora - timedelta(days=90)},
        )
    ).all():
        datas.setdefault(aid, set()).add(d)

    linhas = []
    for a in alunos:
        atual, melhor = _sequencias(datas.get(a["id"], set()), agora.date())
        valor = {"treinos": a["treinos"], "volume": round(a["volume"]), "sequencia": atual}[metrica]
        linhas.append(
            {
                "id": a["id"],
                "nome": nome_publico(a["nome"]),
                "valor": valor,
                "treinos": a["treinos"],
                "melhor_sequencia": melhor,
            }
        )
    linhas.sort(key=lambda x: (-x["valor"], -x["treinos"], x["nome"]))
    for i, x in enumerate(linhas, start=1):
        x["posicao"] = i
        x["eu"] = x.pop("id") == str(aluno_id)

    topo = linhas[:10]
    eu = next((x for x in linhas if x["eu"]), None)
    return {
        "participando": True,
        "metrica": metrica,
        "dias": dias,
        "total": len(linhas),
        "itens": topo,
        "eu": eu if eu and eu not in topo else None,
    }
