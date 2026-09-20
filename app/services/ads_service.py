"""Escolha de anúncio para o card de descanso do app do aluno.

Fase 1 (aqui): stub de leitura. Só lê a cabeça de `ads:rotation:{academia_id}`
no Redis, sem lógica de pacing/orçamento/horário — isso é responsabilidade do
worker assíncrono (Celery/ARQ, docs/01-arquitetura.md e docs/06-stripe-connect.md),
que ainda não existe. Se a chave estiver vazia (ninguém populou ainda, ou sem
verba disponível), retorna None e o app simplesmente não mostra o card de
anúncio (comportamento já prescrito em docs/03-design-tokens.md: `showAd`).

TODO(fase2): quando o gateway WebSocket existir, publicar em
`chan:tv:{academia_id}` a partir de `treino_service.registrar_descanso` para
que a TV troque o criativo em tempo real (evento `ad.show` de docs/05).
"""

from uuid import UUID

from redis.asyncio import Redis

from app.schemas.treino import AnuncioStubOut


async def escolher_anuncio(redis: Redis, *, academia_id: UUID) -> AnuncioStubOut | None:
    raw = await redis.lindex(f"ads:rotation:{academia_id}", 0)
    if not raw:
        return None
    return AnuncioStubOut.model_validate_json(raw)
