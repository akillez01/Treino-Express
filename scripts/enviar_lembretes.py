"""Envia os lembretes de sequência de todas as academias (rodar 1x por dia via cron).

    0 18 * * *  cd /caminho/treino-express-app && PYTHONPATH=. uv run python scripts/enviar_lembretes.py

Lista as academias como superusuário e envia dentro de cada tenant (RLS ativo).
Sem credenciais do WhatsApp no .env os lembretes ficam "simulados"."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.tenant import tenant_session
from app.services import lembretes_service


async def main() -> None:
    engine = create_async_engine(settings.migrations_database_url)
    async with engine.connect() as conn:
        academias = (
            (await conn.execute(text("SELECT id::text FROM academias WHERE ativa"))).scalars().all()
        )
    await engine.dispose()
    total = 0
    for academia in academias:
        async with tenant_session(academia) as db:
            resultados = await lembretes_service.enviar(db, academia)
        total += len(resultados)
        if resultados:
            print(f"{academia}: {len(resultados)} lembretes ({resultados[0]['status']})")
    print(f"Total: {total} lembretes.")


if __name__ == "__main__":
    asyncio.run(main())
