import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/demo", response_model=TokenOut)
async def login_demo() -> TokenOut:
    """Token do aluno demo — só existe com ENABLE_DEMO_LOGIN=true."""
    if not settings.enable_demo_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    aluno_id = uuid.UUID(settings.demo_aluno_id)
    token = create_access_token(
        subject=str(aluno_id),
        type="aluno",
        academia_id=uuid.UUID(settings.demo_academia_id),
        aluno_id=aluno_id,
    )
    return TokenOut(access_token=token)
