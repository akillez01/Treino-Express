"""Isolamento multi-tenant via Row Level Security do Postgres.

Regra inegociável: o tenant setado via `set_config('app.academia_id', ..., true)`
(equivalente a `SET LOCAL`, mas como função — `SET LOCAL x = $1` não é sintaxe
válida no Postgres, `SET` não aceita bind parameter, só literal) só vale
dentro da transação em que foi executado. Por isso cada request abre sua
própria `AsyncSession`, inicia a transação explicitamente, seta o tenant como
primeiro statement, e fecha tudo (commit/rollback) antes da conexão voltar ao
pool — nunca reusar uma sessão entre requests, nunca setar sem o `true` de
`is_local` (que é o que dá o efeito "LOCAL", escopado à transação).

Toda rota autenticada deve depender de `get_tenant_db` (ou de uma variante
tenant-aware como `get_tenant_db_from_path`), nunca de uma sessão "crua" sem
tenant — isso é o que garante que é estruturalmente difícil esquecer o
isolamento numa rota nova.
"""

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.security_deps import get_current_user
from app.core.security import TokenPayload
from app.db.session import AsyncSessionLocal

_SET_TENANT_SQL = text("SELECT set_config('app.academia_id', :academia_id, true)")
_SET_ANUNCIANTE_SQL = text("SELECT set_config('app.anunciante_id', :anunciante_id, true)")


async def get_tenant_db(
    current_user: TokenPayload = Depends(get_current_user),
) -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(_SET_TENANT_SQL, {"academia_id": str(current_user.academia_id)})
            yield session


async def get_tenant_db_for_academia(academia_id: str) -> AsyncIterator[AsyncSession]:
    """Variante para rotas sem JWT de aluno/gestor onde o tenant é resolvido a
    partir do path (ex.: `GET /r/{campanha_id}/{nonce}` do scan de QR). O
    chamador é responsável por validar `academia_id` antes de usar isso."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(_SET_TENANT_SQL, {"academia_id": academia_id})
            yield session


async def get_anunciante_db(
    current_user: TokenPayload = Depends(get_current_user),
) -> AsyncIterator[AsyncSession]:
    """Sessão do painel do anunciante: seta `app.anunciante_id` (o anunciante
    atua em várias academias, então nenhum `app.academia_id` é definido). Só
    aceita token do tipo `anunciante`."""
    if current_user.type != "anunciante":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token não é de anunciante")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(_SET_ANUNCIANTE_SQL, {"anunciante_id": current_user.sub})
            yield session
