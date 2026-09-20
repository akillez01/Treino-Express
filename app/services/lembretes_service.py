"""Lembretes de sequência quebrada.

Candidato = aluno que vinha treinando (3+ dias ativos nos 30 dias antes da pausa)
e está há 3 a 30 dias sem treinar nem fazer check-in. Só recebe mensagem quem
aceitou lembretes e tem telefone, no máximo uma vez a cada 7 dias. Quem não
aceitou aparece para a academia, sem envio automático."""

from datetime import date, datetime, timedelta
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.integrations.whatsapp import client as whatsapp
from app.services.progresso_service import TZ

DIAS_SEM_TREINAR = 3
DIAS_SEM_TREINAR_MAX = 30
MIN_DIAS_ATIVOS = 3
MIN_SEQUENCIA = 2  # só conta como "quebrou a sequência" quem tinha pelo menos 2 dias seguidos
COOLDOWN_DIAS = 7


def _run_ate(dias: set[date], fim: date) -> int:
    n, d = 0, fim
    while d in dias:
        n += 1
        d -= timedelta(days=1)
    return n


def _mascarar(tel: str | None) -> str | None:
    if not tel:
        return None
    return f"+{tel[:2]} {tel[2:4]} ••••{tel[-4:]}"


def montar_mensagem(nome: str, sequencia: int, academia: str, link: str) -> str:
    primeiro = nome.split()[0]
    if sequencia >= 2:
        parte = f"Sua sequência de {sequencia} dias na {academia} parou."
    else:
        parte = f"Sentimos sua falta na {academia}."
    return f"Oi, {primeiro}! {parte} Que tal um treino rápido de 20 minutos hoje? {link}"


async def _academia_nome(db: AsyncSession) -> str:
    return (
        await db.execute(text("SELECT nome FROM academias WHERE id = tenant_atual()"))
    ).scalar() or "academia"


async def candidatos(db: AsyncSession) -> list[dict]:
    hoje = datetime.now(TZ).date()
    academia = await _academia_nome(db)
    link = f"{settings.public_web_url}/aluno"

    alunos = (
        (
            await db.execute(
                text(
                    "SELECT id::text, nome, telefone, lembretes_whatsapp FROM alunos "
                    "WHERE cancelado_em IS NULL"
                )
            )
        )
        .mappings()
        .all()
    )
    atividade: dict[str, set[date]] = {}
    for aid, d in (
        await db.execute(
            text(
                """
                SELECT aluno_id::text, (concluido_em AT TIME ZONE 'America/Sao_Paulo')::date
                  FROM treinos WHERE concluido_em > now() - interval '75 days'
                UNION
                SELECT aluno_id::text, (entrada_em AT TIME ZONE 'America/Sao_Paulo')::date
                  FROM check_ins WHERE entrada_em > now() - interval '75 days'
                """
            )
        )
    ).all():
        atividade.setdefault(aid, set()).add(d)
    ultimo_envio = {
        aid: dt
        for aid, dt in (
            await db.execute(
                text("SELECT aluno_id::text, max(criado_em) FROM lembretes GROUP BY aluno_id")
            )
        ).all()
    }

    saida = []
    for a in alunos:
        dias = atividade.get(a["id"])
        if not dias:
            continue
        ultimo = max(dias)
        parado = (hoje - ultimo).days
        if not DIAS_SEM_TREINAR <= parado <= DIAS_SEM_TREINAR_MAX:
            continue
        ativos_antes = sum(1 for d in dias if ultimo - timedelta(days=30) < d <= ultimo)
        if ativos_antes < MIN_DIAS_ATIVOS:
            continue
        seq = _run_ate(dias, ultimo)
        if seq < MIN_SEQUENCIA:
            continue
        tel = whatsapp.normalizar_telefone(a["telefone"] or "")
        envio = ultimo_envio.get(a["id"])
        bloqueio = None
        if not a["lembretes_whatsapp"]:
            bloqueio = "sem_consentimento"
        elif not tel:
            bloqueio = "sem_telefone"
        elif envio and (datetime.now(TZ) - envio).days < COOLDOWN_DIAS:
            bloqueio = "enviado_recentemente"
        msg = montar_mensagem(a["nome"], seq, academia, link)
        saida.append(
            {
                "aluno_id": a["id"],
                "nome": a["nome"],
                "dias_sem_treinar": parado,
                "sequencia_perdida": seq,
                "dias_ativos_30d": ativos_antes,
                "telefone": _mascarar(tel),
                "pode_enviar": bloqueio is None,
                "bloqueio": bloqueio,
                "mensagem": msg,
                # abre a conversa no WhatsApp do próprio funcionário (envio manual)
                "wa_link": f"https://wa.me/{tel}?text={quote(msg)}" if tel else None,
            }
        )
    saida.sort(key=lambda x: (not x["pode_enviar"], -x["sequencia_perdida"], x["nome"]))
    return saida


async def historico(db: AsyncSession, limite: int = 30) -> list[dict]:
    r = await db.execute(
        text(
            "SELECT l.id::text, a.nome, l.status, l.mensagem, l.erro, l.criado_em "
            "FROM lembretes l JOIN alunos a ON a.id = l.aluno_id "
            "ORDER BY l.criado_em DESC LIMIT :n"
        ),
        {"n": limite},
    )
    return [dict(x) for x in r.mappings().all()]


async def enviar(
    db: AsyncSession, academia_id: UUID, aluno_ids: set[str] | None = None
) -> list[dict]:
    """Envia (ou simula) os lembretes dos candidatos elegíveis."""
    link = f"{settings.public_web_url}/aluno"
    resultados = []
    for c in await candidatos(db):
        if not c["pode_enviar"] or (aluno_ids is not None and c["aluno_id"] not in aluno_ids):
            continue
        tel = (
            await db.execute(
                text("SELECT telefone FROM alunos WHERE id = CAST(:a AS uuid)"),
                {"a": c["aluno_id"]},
            )
        ).scalar()
        telefone = whatsapp.normalizar_telefone(tel or "")
        status, erro = "simulado", None
        if whatsapp.configurado():
            try:
                await whatsapp.enviar_template(
                    telefone or "",
                    [
                        c["nome"].split()[0],
                        str(max(c["sequencia_perdida"], c["dias_ativos_30d"])),
                        link,
                    ],
                )
                status = "enviado"
            except whatsapp.WhatsAppErro as exc:
                status, erro = "falhou", str(exc)
        await db.execute(
            text(
                "INSERT INTO lembretes (academia_id, aluno_id, status, mensagem, erro) "
                "VALUES (CAST(:ac AS uuid), CAST(:al AS uuid), :s, :m, :e)"
            ),
            {
                "ac": str(academia_id),
                "al": c["aluno_id"],
                "s": status,
                "m": c["mensagem"],
                "e": erro,
            },
        )
        resultados.append(
            {"aluno_id": c["aluno_id"], "nome": c["nome"], "status": status, "erro": erro}
        )
    return resultados
