"""Escolha e contabilização de anúncios da TV.

`proximo_anuncio` faz round-robin entre as campanhas elegíveis da academia
(ativas, dentro da janela de datas e de horário, com verba restante) e emite o
evento `ad.show`. Cada exibição recebe um nonce rotativo: ele vai no QR e só
vale uma vez, o que impede reaproveitar um QR fotografado. Pacing por verba
diária e cobrança ficam para o worker (docs/01-arquitetura.md).
"""

import secrets

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

NONCE_TTL_S = 3600

_ELEGIVEIS = text(
    """
    SELECT c.id::text AS campanha_id, c.duracao_exibicao_s, c.desconto_rotulo, c.manchete,
           c.corpo, c.cupom, an.nome AS marca, an.categoria, an.distancia_metros
    FROM campanhas_ads c JOIN anunciantes an ON an.id = c.anunciante_id
    WHERE c.status = 'ativa' AND an.ativo
      AND c.inicio <= CURRENT_DATE AND (c.fim IS NULL OR c.fim >= CURRENT_DATE)
      AND (now() AT TIME ZONE 'America/Sao_Paulo')::time BETWEEN c.hora_inicio AND c.hora_fim
      AND c.gasto_centavos < c.orcamento_centavos
    ORDER BY c.id
    """
)


def _nonce_key(campanha_id: str, nonce: str) -> str:
    return f"ads:nonce:{campanha_id}:{nonce}"


async def proximo_anuncio(db: AsyncSession, redis: Redis, academia_id) -> dict | None:
    rows = (await db.execute(_ELEGIVEIS)).mappings().all()
    if not rows:
        return None
    cursor = await redis.incr(f"ads:cursor:{academia_id}")
    i = (cursor - 1) % len(rows)
    c = rows[i]

    nonce = secrets.token_hex(6)
    await redis.set(_nonce_key(c["campanha_id"], nonce), "1", ex=NONCE_TTL_S)

    categoria = c["categoria"] or ""
    if c["distancia_metros"]:
        categoria = f"{categoria} · {c['distancia_metros']} m da academia".strip(" ·")
    return {
        "type": "ad.show",
        "campanha_id": c["campanha_id"],
        "nonce": nonce,
        "duracao_s": int(c["duracao_exibicao_s"]),
        "criativo": {
            "marca": c["marca"],
            "categoria": categoria,
            "desconto": c["desconto_rotulo"],
            "manchete": c["manchete"],
            "corpo": c["corpo"],
            "cupom": c["cupom"],
            "qr_url": f"{settings.public_api_url}/r/{c['campanha_id']}/{nonce}",
        },
        "posicao": {"atual": i + 1, "total": len(rows)},
    }


async def registrar_impressao(
    db: AsyncSession, redis: Redis, *, tela_id: str, campanha_id: str, nonce: str
) -> bool:
    """Grava a impressão que a TV confirmou. Só aceita nonces emitidos por nós
    (consumidos uma única vez) e campanhas da própria academia."""
    if not await redis.getdel(_nonce_key(campanha_id, nonce)):
        return False
    r = await db.execute(
        text(
            """
            INSERT INTO impressoes (academia_id, campanha_id, tela_id, nonce, custo_centavos)
            SELECT tenant_atual(), c.id, CAST(:tela AS uuid), :nonce,
                   round(c.cpm_centavos / 1000.0)::int
            FROM campanhas_ads c
            WHERE c.id = CAST(:campanha AS uuid) AND c.academia_id = tenant_atual()
            ON CONFLICT (campanha_id, nonce) DO NOTHING
            RETURNING id
            """
        ),
        {"tela": tela_id, "campanha": campanha_id, "nonce": nonce},
    )
    return r.first() is not None
