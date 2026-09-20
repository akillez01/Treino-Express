import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    academia_id: str | None = None
    tela_id: str | None = None


@router.post("/demo", response_model=TokenOut)
async def login_demo(
    perfil: Literal["aluno", "gestor", "anunciante", "tela"] = "aluno",
) -> TokenOut:
    """Token de demonstração por perfil — só existe com ENABLE_DEMO_LOGIN=true.
    Enquanto o login real (usuário e senha) não existe, cada perfil aponta para
    a academia/aluno/anunciante demo definidos em settings."""
    if not settings.enable_demo_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    academia_id = uuid.UUID(settings.demo_academia_id)
    if perfil == "tela":
        tela_id = uuid.UUID(settings.demo_tela_id)
        token = create_access_token(subject=str(tela_id), type="tela", academia_id=academia_id)
        return TokenOut(access_token=token, academia_id=str(academia_id), tela_id=str(tela_id))
    if perfil == "anunciante":
        anunciante_id = uuid.UUID(settings.demo_anunciante_id)
        token = create_access_token(subject=str(anunciante_id), type="anunciante")
    elif perfil == "gestor":
        token = create_access_token(
            subject=str(academia_id), type="gestor", academia_id=academia_id
        )
    else:
        aluno_id = uuid.UUID(settings.demo_aluno_id)
        token = create_access_token(
            subject=str(aluno_id), type="aluno", academia_id=academia_id, aluno_id=aluno_id
        )
    return TokenOut(access_token=token)
