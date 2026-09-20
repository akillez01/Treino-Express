import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pydantic import BaseModel

from app.core.config import settings

TokenType = Literal["aluno", "gestor", "anunciante", "tela"]

_EXPIRE_MINUTES: dict[TokenType, int] = {
    "aluno": settings.jwt_expire_minutes_aluno,
    "gestor": settings.jwt_expire_minutes_gestor,
    "anunciante": settings.jwt_expire_minutes_anunciante,
    "tela": settings.jwt_expire_minutes_tela,
}


class TokenPayload(BaseModel):
    sub: str
    type: TokenType
    academia_id: uuid.UUID | None = None
    aluno_id: uuid.UUID | None = None
    exp: int
    iat: int


def create_access_token(
    *,
    subject: str,
    type: TokenType,
    academia_id: uuid.UUID | None = None,
    aluno_id: uuid.UUID | None = None,
) -> str:
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=_EXPIRE_MINUTES[type])
    payload = {
        "sub": subject,
        "type": type,
        "academia_id": str(academia_id) if academia_id else None,
        "aluno_id": str(aluno_id) if aluno_id else None,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    return TokenPayload(**raw)
