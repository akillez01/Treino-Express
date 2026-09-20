"""Desempenho e evolução do aluno, calculados a partir do histórico de treinos.

Só conta o que o aluno concluiu. Carga vem do texto do exercício ("Carga 40 kg",
"2x14 kg"): o número antes de "kg". Exercícios sem kg (peso do corpo, minutos)
entram em frequência e conclusão, mas não em volume nem em recordes.
"""

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TZ = ZoneInfo("America/Sao_Paulo")
_KG = re.compile(r"(\d+(?:[.,]\d+)?)\s*kg", re.I)
_SERIES = re.compile(r"^\s*(\d+)\s*x\s*(\d+)")
MAX_MIN_TREINO = 180  # descarta treinos "esquecidos" abertos por horas

CONQUISTAS = [
    ("primeiro_treino", "Primeiro treino", "Conclua seu primeiro treino"),
    ("sequencia_3", "Embalado", "3 dias seguidos treinando"),
    ("sequencia_7", "Semana perfeita", "7 dias seguidos treinando"),
    ("dez_treinos", "Dez treinos", "Conclua 10 treinos"),
    ("vinte_cinco_treinos", "Veterano", "Conclua 25 treinos"),
    ("volume_1t", "Uma tonelada", "Levante 1.000 kg de volume total"),
    ("meta_semana", "Meta batida", "Cumpra a meta de treinos da semana"),
    ("novo_recorde", "Recorde pessoal", "Bata um recorde de carga nos últimos 7 dias"),
    ("meta_exercicio", "Objetivo cumprido", "Alcance a meta de carga de um exercício"),
]


def _kg(carga: str | None) -> float | None:
    m = _KG.search(carga or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _sets_reps(series: str | None) -> tuple[int, int]:
    m = _SERIES.match(series or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _volume(carga: str | None, series: str | None) -> float:
    kg = _kg(carga)
    sets, reps = _sets_reps(series)
    return kg * sets * reps if kg and sets and reps else 0.0


def _local(dt: datetime) -> date:
    return dt.astimezone(TZ).date()


def _segunda(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _sequencias(dias: set[date], hoje: date) -> tuple[int, int]:
    """(sequência atual, melhor sequência). A atual continua valendo até ontem."""
    if not dias:
        return 0, 0
    ordenados = sorted(dias)
    melhor = atual_run = 1
    for a, b in zip(ordenados, ordenados[1:], strict=False):
        atual_run = atual_run + 1 if (b - a).days == 1 else 1
        melhor = max(melhor, atual_run)
    ultimo = ordenados[-1]
    if (hoje - ultimo).days > 1:
        return 0, melhor
    atual = 1
    d = ultimo
    while d - timedelta(days=1) in dias:
        d -= timedelta(days=1)
        atual += 1
    return atual, melhor


async def _linhas(db: AsyncSession, aluno_id: UUID, desde: datetime):
    r = await db.execute(
        text(
            """
            SELECT t.id::text AS treino_id, t.foco::text AS foco, t.iniciado_em, t.concluido_em,
                   t.esforco, te.exercicio_id::text AS exercicio_id, ex.nome,
                   te.series, te.carga, te.concluido_em AS ex_concluido_em
            FROM treinos t
            JOIN treino_exercicios te ON te.treino_id = t.id
            JOIN exercicios ex ON ex.id = te.exercicio_id
            WHERE t.aluno_id = CAST(:a AS uuid) AND t.iniciado_em >= :desde
            ORDER BY t.iniciado_em, te.ordem
            """
        ),
        {"a": str(aluno_id), "desde": desde},
    )
    return [dict(x) for x in r.mappings().all()]


async def progresso(db: AsyncSession, aluno_id: UUID, dias: int = 90) -> dict:
    agora = datetime.now(TZ)
    hoje = agora.date()
    linhas = await _linhas(db, aluno_id, agora - timedelta(days=max(dias, 60)))
    meta = (
        await db.execute(
            text("SELECT meta_semanal FROM alunos WHERE id = CAST(:a AS uuid)"),
            {"a": str(aluno_id)},
        )
    ).scalar() or 3

    treinos: dict[str, dict] = {}
    for x in linhas:
        t = treinos.setdefault(
            x["treino_id"],
            {
                "foco": x["foco"],
                "iniciado_em": x["iniciado_em"],
                "concluido_em": x["concluido_em"],
                "esforco": x["esforco"],
                "planejados": 0,
                "feitos": 0,
                "volume": 0.0,
            },
        )
        t["planejados"] += 1
        if x["ex_concluido_em"]:
            t["feitos"] += 1
            t["volume"] += _volume(x["carga"], x["series"])

    concluidos = {k: v for k, v in treinos.items() if v["concluido_em"]}
    datas = {_local(v["concluido_em"]) for v in concluidos.values()}
    atual, melhor = _sequencias(datas, hoje)

    # --- semanas (últimas 8, da mais antiga para a atual)
    seg_atual = _segunda(hoje)
    semanas = []
    for i in range(7, -1, -1):
        ini = seg_atual - timedelta(weeks=i)
        do_periodo = [
            v
            for v in concluidos.values()
            if ini <= _local(v["concluido_em"]) < ini + timedelta(days=7)
        ]
        semanas.append(
            {
                "inicio": ini.isoformat(),
                "treinos": len(do_periodo),
                "volume_kg": round(sum(v["volume"] for v in do_periodo)),
            }
        )
    treinos_semana = semanas[-1]["treinos"]

    # --- foco, tempo e volume totais
    por_foco: dict[str, int] = defaultdict(int)
    minutos = 0
    volume_total = 0.0
    exercicios_feitos = 0
    for v in concluidos.values():
        por_foco[v["foco"]] += 1
        dur = (v["concluido_em"] - v["iniciado_em"]).total_seconds() / 60
        minutos += min(max(dur, 0), MAX_MIN_TREINO)
        volume_total += v["volume"]
        exercicios_feitos += v["feitos"]

    # --- recordes e evolução de carga por exercício
    historico: dict[str, list[tuple[date, float]]] = defaultdict(list)
    nomes: dict[str, str] = {}
    for x in linhas:
        kg = _kg(x["carga"])
        if x["ex_concluido_em"] and kg:
            # o mesmo exercício pode existir em mais de um foco do catálogo: agrupa pelo nome
            historico[x["nome"]].append((_local(x["ex_concluido_em"]), kg))
            nomes[x["nome"]] = x["nome"]
    recordes, evolucao = [], []
    for ex_id, pts in historico.items():
        por_dia: dict[date, float] = {}
        for d, kg in pts:
            por_dia[d] = max(por_dia.get(d, 0), kg)
        serie = sorted(por_dia.items())
        melhor_kg = max(kg for _, kg in serie)
        quando = next(d for d, kg in serie if kg == melhor_kg)
        primeira = serie[0][1]
        recordes.append(
            {
                "exercicio": nomes[ex_id],
                "kg": melhor_kg,
                "data": quando.isoformat(),
                "evolucao_kg": round(melhor_kg - primeira, 1),
                "sessoes": len(serie),
            }
        )
        evolucao.append(
            {
                "exercicio": nomes[ex_id],
                "pontos": [{"data": d.isoformat(), "kg": kg} for d, kg in serie],
            }
        )
    melhor_por_ex = {nome: max(kg for _, kg in pts) for nome, pts in historico.items()}
    ritmo_por_ex = {}
    for nome, pts in historico.items():
        por_dia2: dict[date, float] = {}
        for d, kg in pts:
            por_dia2[d] = max(por_dia2.get(d, 0), kg)
        ritmo_por_ex[nome] = _ritmo_kg_semana(sorted(por_dia2.items()))
    lista_metas = await metas(db, aluno_id, melhor_por_ex, ritmo_por_ex)
    opcoes = sorted(
        {
            n
            for (n,) in (
                await db.execute(
                    text(
                        "SELECT DISTINCT nome FROM exercicios WHERE carga_sugerida ~* '[0-9] *kg' "
                        "AND ativo ORDER BY nome"
                    )
                )
            ).all()
        }
        | set(melhor_por_ex)
    )
    recordes.sort(key=lambda r: (-r["evolucao_kg"], -r["kg"]))
    evolucao.sort(key=lambda e: -len(e["pontos"]))
    recorde_recente = any(
        (hoje - date.fromisoformat(r["data"])).days <= 7 and r["evolucao_kg"] > 0 for r in recordes
    )

    # --- pontuação (0-100): consistência 50 + progressão 30 + conclusão 20
    ini4 = hoje - timedelta(days=28)
    ult4 = [v for v in concluidos.values() if _local(v["concluido_em"]) >= ini4]
    consistencia = min(1.0, len(ult4) / (meta * 4)) if meta else 0
    prs30 = sum(
        1
        for r in recordes
        if r["evolucao_kg"] > 0 and (hoje - date.fromisoformat(r["data"])).days <= 30
    )
    progressao = min(1.0, prs30 / 5)
    rec30 = [v for v in treinos.values() if _local(v["iniciado_em"]) >= hoje - timedelta(days=30)]
    plan = sum(v["planejados"] for v in rec30)
    conclusao = (sum(v["feitos"] for v in rec30) / plan) if plan else 0
    pontos = round(consistencia * 50 + progressao * 30 + conclusao * 20)
    nivel = (
        "Elite"
        if pontos >= 85
        else "Consistente"
        if pontos >= 60
        else "Em evolução"
        if pontos >= 30
        else "Começando"
    )

    n = len(concluidos)
    conquistadas = {
        "primeiro_treino": n >= 1,
        "sequencia_3": melhor >= 3,
        "sequencia_7": melhor >= 7,
        "dez_treinos": n >= 10,
        "vinte_cinco_treinos": n >= 25,
        "volume_1t": volume_total >= 1000,
        "meta_semana": treinos_semana >= meta,
        "novo_recorde": recorde_recente,
        "meta_exercicio": any(m["atingida"] for m in lista_metas),
    }

    return {
        "meta_semanal": meta,
        "semana": {"treinos": treinos_semana, "meta": meta},
        "sequencia": {"atual": atual, "melhor": melhor},
        "totais": {
            "treinos": n,
            "minutos": round(minutos),
            "exercicios": exercicios_feitos,
            "volume_kg": round(volume_total),
        },
        "semanas": semanas,
        "por_foco": [
            {"foco": f, "treinos": c} for f, c in sorted(por_foco.items(), key=lambda i: -i[1])
        ],
        "recordes": recordes[:6],
        "evolucao_carga": evolucao[:3],
        "metas": lista_metas,
        "opcoes_meta": opcoes,
        "pontuacao": {
            "total": pontos,
            "nivel": nivel,
            "consistencia": round(consistencia * 50),
            "progressao": round(progressao * 30),
            "conclusao": round(conclusao * 20),
        },
        "conquistas": [
            {"id": i, "titulo": t, "descricao": d, "conquistada": conquistadas[i]}
            for i, t, d in CONQUISTAS
        ],
    }


async def resumo_treino(db: AsyncSession, aluno_id: UUID, treino_id: UUID) -> dict | None:
    """Resumo de um treino: tempo, volume e recordes batidos nele."""
    rows = (
        (
            await db.execute(
                text(
                    """
                    SELECT t.iniciado_em, t.concluido_em, t.esforco, t.foco::text AS foco,
                           te.exercicio_id::text AS exercicio_id, ex.nome, te.series, te.carga,
                           te.concluido_em AS ex_em
                    FROM treinos t JOIN treino_exercicios te ON te.treino_id = t.id
                    JOIN exercicios ex ON ex.id = te.exercicio_id
                    WHERE t.id = CAST(:t AS uuid) AND t.aluno_id = CAST(:a AS uuid)
                    ORDER BY te.ordem
                    """
                ),
                {"t": str(treino_id), "a": str(aluno_id)},
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    ini, fim = rows[0]["iniciado_em"], rows[0]["concluido_em"] or datetime.now(TZ)
    feitos = [r for r in rows if r["ex_em"]]
    prs = []
    for r in feitos:
        kg = _kg(r["carga"])
        if not kg:
            continue
        anterior = (
            await db.execute(
                text(
                    """
                    SELECT te.carga FROM treino_exercicios te
                    JOIN treinos t ON t.id = te.treino_id
                    WHERE t.aluno_id = CAST(:a AS uuid) AND te.exercicio_id = CAST(:e AS uuid)
                      AND te.concluido_em IS NOT NULL AND t.id <> CAST(:t AS uuid)
                      AND te.concluido_em < :fim
                    """
                ),
                {"a": str(aluno_id), "e": r["exercicio_id"], "t": str(treino_id), "fim": fim},
            )
        ).scalars()
        antes = [k for k in (_kg(c) for c in anterior) if k]
        if antes and kg > max(antes):
            prs.append({"exercicio": r["nome"], "kg": kg, "anterior_kg": max(antes)})
    return {
        "treino_id": str(treino_id),
        "foco": rows[0]["foco"],
        "duracao_min": round(min((fim - ini).total_seconds() / 60, MAX_MIN_TREINO)),
        "exercicios_concluidos": len(feitos),
        "exercicios_total": len(rows),
        "volume_kg": round(sum(_volume(r["carga"], r["series"]) for r in feitos)),
        "recordes": prs,
        "esforco": rows[0]["esforco"],
    }


async def gravar_volume(db: AsyncSession, treino_id: UUID) -> float:
    """Guarda o volume do treino ao concluir (alimenta o ranking sem recalcular tudo)."""
    rows = (
        await db.execute(
            text(
                "SELECT carga, series FROM treino_exercicios "
                "WHERE treino_id = CAST(:t AS uuid) AND concluido_em IS NOT NULL"
            ),
            {"t": str(treino_id)},
        )
    ).all()
    volume = round(sum(_volume(c, s) for c, s in rows), 1)
    await db.execute(
        text("UPDATE treinos SET volume_kg = :v WHERE id = CAST(:t AS uuid)"),
        {"v": volume, "t": str(treino_id)},
    )
    return volume


def _ritmo_kg_semana(serie: list[tuple[date, float]]) -> float:
    """Ganho médio de carga por semana entre a primeira e a última sessão."""
    if len(serie) < 2:
        return 0.0
    dias = (serie[-1][0] - serie[0][0]).days
    return (serie[-1][1] - serie[0][1]) / (dias / 7) if dias > 0 else 0.0


async def metas(
    db: AsyncSession, aluno_id: UUID, melhor: dict[str, float], ritmo: dict[str, float]
) -> list[dict]:
    rows = (
        (
            await db.execute(
                text(
                    "SELECT exercicio, alvo_kg::float AS alvo, prazo, atingida_em "
                    "FROM metas_exercicio WHERE aluno_id = CAST(:a AS uuid) ORDER BY criada_em"
                ),
                {"a": str(aluno_id)},
            )
        )
        .mappings()
        .all()
    )
    hoje = datetime.now(TZ).date()
    saida = []
    for m in rows:
        atual = melhor.get(m["exercicio"], 0.0)
        atingida = atual >= m["alvo"]
        atingida_em = m["atingida_em"]
        if atingida and atingida_em is None:  # registra o dia em que bateu a meta
            atingida_em = datetime.now(TZ)
            await db.execute(
                text(
                    "UPDATE metas_exercicio SET atingida_em = :q "
                    "WHERE aluno_id = CAST(:a AS uuid) AND exercicio = :e"
                ),
                {"q": atingida_em, "a": str(aluno_id), "e": m["exercicio"]},
            )
        falta = max(0.0, m["alvo"] - atual)
        r = ritmo.get(m["exercicio"], 0.0)
        previsao = round(falta / (r / 7)) if not atingida and r > 0 else None
        saida.append(
            {
                "exercicio": m["exercicio"],
                "alvo_kg": m["alvo"],
                "atual_kg": atual,
                "pct": min(100, round(atual / m["alvo"] * 100)) if m["alvo"] else 0,
                "atingida": atingida,
                "prazo": m["prazo"].isoformat() if m["prazo"] else None,
                "dias_restantes": (m["prazo"] - hoje).days if m["prazo"] else None,
                "previsao_dias": previsao,
            }
        )
    return saida
