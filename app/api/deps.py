from fastapi import Depends, HTTPException, status

from app.api.security_deps import get_current_user
from app.core.security import TokenPayload

# Re-exportado para as rotas: `Depends(get_tenant_db)` é a forma padrão de
# obter uma AsyncSession com o tenant já setado via SET LOCAL.
from app.db.tenant import get_tenant_db  # noqa: F401


def _require_type(payload: TokenPayload, expected: str) -> TokenPayload:
    if payload.type != expected:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Token de tipo '{payload.type}' não pode acessar rota de '{expected}'",
        )
    return payload


async def get_current_aluno(current: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    return _require_type(current, "aluno")


async def get_current_gestor(current: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    return _require_type(current, "gestor")


async def get_current_anunciante(current: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    return _require_type(current, "anunciante")


async def get_current_tela(current: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    return _require_type(current, "tela")
