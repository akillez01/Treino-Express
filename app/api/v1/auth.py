import uuid
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.security import create_access_token
from app.db.tenant import tenant_session
from app.models.aluno import Aluno

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    academia_id: str | None = None
    aluno_id: str | None = None
    tela_id: str | None = None


class GoogleConfigOut(BaseModel):
    enabled: bool
    client_id: str
    hosted_domain: str = ""


class GoogleCredentialIn(BaseModel):
    credential: str = Field(min_length=1, max_length=16_384)


GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


@router.get("/google/config", response_model=GoogleConfigOut)
async def google_config() -> GoogleConfigOut:
    return GoogleConfigOut(
        enabled=bool(settings.google_login_enabled and settings.google_client_id),
        client_id=settings.google_client_id,
        hosted_domain=settings.google_allowed_hosted_domain,
    )


async def _verify_google_credential(credential: str) -> dict[str, str]:
    if not settings.google_client_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Login do Google não está configurado no servidor.",
        )
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            response = await http.get(GOOGLE_TOKENINFO_URL, params={"id_token": credential})
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Não foi possível validar a credencial do Google.",
        ) from exc
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credencial do Google inválida.")
    try:
        claims = response.json()
    except ValueError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Resposta inválida do Google.") from exc
    if not isinstance(claims, dict):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credencial do Google inválida.")

    if claims.get("aud") != settings.google_client_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credencial do Google não pertence a este app."
        )
    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Emissor da credencial do Google inválido."
        )
    if str(claims.get("email_verified", "")).lower() != "true":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "A conta Google precisa ter o e-mail verificado."
        )
    email = claims.get("email")
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credencial do Google sem e-mail.")
    try:
        expires_at = int(claims["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Credencial do Google sem validade."
        ) from exc
    if expires_at <= int(datetime.now(UTC).timestamp()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credencial do Google expirada.")
    if (
        settings.google_allowed_hosted_domain
        and claims.get("hd") != settings.google_allowed_hosted_domain
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "A conta Google não pertence ao domínio permitido."
        )
    return {"email": email.strip().casefold()}


@router.post("/google", response_model=TokenOut)
async def login_google(body: GoogleCredentialIn) -> TokenOut:
    if not settings.google_login_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Login do Google não está habilitado.")
    claims = await _verify_google_credential(body.credential)
    if not settings.google_default_academia_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Configure GOOGLE_DEFAULT_ACADEMIA_ID para habilitar o login do Google.",
        )
    try:
        academia_id = uuid.UUID(settings.google_default_academia_id)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "GOOGLE_DEFAULT_ACADEMIA_ID inválido.",
        ) from exc

    # A sessão define o tenant via SET LOCAL antes da consulta. Não há
    # conexão privilegiada nem leitura global que contorne o RLS.
    async with tenant_session(str(academia_id)) as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        alunos = (
            await db.scalars(select(Aluno).where(func.lower(Aluno.email) == claims["email"]))
        ).all()
    if not alunos:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Nenhum aluno cadastrado nesta academia usa este e-mail Google.",
        )
    if len(alunos) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este e-mail está associado a mais de um aluno; selecione a academia.",
        )
    aluno = alunos[0]
    token = create_access_token(
        subject=str(aluno.id),
        type="aluno",
        academia_id=aluno.academia_id,
        aluno_id=aluno.id,
    )
    return TokenOut(
        access_token=token,
        academia_id=str(aluno.academia_id),
        aluno_id=str(aluno.id),
    )


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
