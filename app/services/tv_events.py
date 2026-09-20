"""Eventos servidor -> TV (docs/05). Cada academia tem um canal Redis
`chan:tv:{academia_id}`; o gateway WebSocket de cada tela assina esse canal.
Um evento com `tela_id` só vale para aquela tela; sem `tela_id`, vale para todas."""

import json

from redis.asyncio import Redis


def canal(academia_id) -> str:
    return f"chan:tv:{academia_id}"


async def publicar(redis: Redis, academia_id, evento: dict) -> None:
    await redis.publish(canal(academia_id), json.dumps(evento, default=str))
