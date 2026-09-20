"""Dependency de autenticação de baixo nível — só decodifica o JWT.

Fica separado de `app/api/deps.py` para evitar import circular: `app/db/tenant.py`
precisa de `get_current_user` para saber qual `academia_id` usar no `SET LOCAL`,
e `app/api/deps.py` depende de `app/db/tenant.py` para as dependencies por perfil
que também precisam de sessão de banco.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import InvalidTokenError, TokenPayload, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> TokenPayload:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente")
    try:
        return decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido ou expirado") from exc
