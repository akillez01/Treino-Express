"""Pareamento da TV e rota pública do QR (atribuição de scan)."""

import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["tv"])
scan_router = APIRouter(tags=["tv"])

TENTATIVAS_POR_MINUTO = 10


class ParearIn(BaseModel):
    codigo: str = Field(min_length=6, max_length=7, pattern=r"^[A-Za-z0-9]{3}-?[A-Za-z0-9]{3}$")


class ParearOut(BaseModel):
    access_token: str
    academia_id: str
    tela_id: str


@router.post("/tv/parear", response_model=ParearOut)
async def parear(body: ParearIn, request: Request):
    """A TV informa o código de pareamento exibido no painel da academia e recebe
    o JWT da tela. O código é de uso único (a função apaga-o ao parear)."""
    ip = request.client.host if request.client else "?"
    redis = get_redis()
    chave = f"parear:tentativas:{ip}"
    tentativas = await redis.incr(chave)
    if tentativas == 1:
        await redis.expire(chave, 60)
    if tentativas > TENTATIVAS_POR_MINUTO:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Muitas tentativas. Aguarde um minuto."
        )

    codigo = body.codigo.upper()
    if "-" not in codigo:
        codigo = f"{codigo[:3]}-{codigo[3:]}"
    async with AsyncSessionLocal() as session, session.begin():
        row = (
            (await session.execute(text("SELECT * FROM parear_tela(:c)"), {"c": codigo}))
            .mappings()
            .first()
        )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Código inválido ou já utilizado")
    token = create_access_token(
        subject=str(row["tela_id"]), type="tela", academia_id=row["academia_id"]
    )
    return ParearOut(
        access_token=token, academia_id=str(row["academia_id"]), tela_id=str(row["tela_id"])
    )


@scan_router.get("/r/{campanha_id}/{nonce}", include_in_schema=False)
async def scan(campanha_id: uuid.UUID, nonce: str):
    """Registra o escaneamento do QR e leva o aluno ao cupom."""
    destino = f"{settings.public_web_url}/cupom"
    if not nonce.isalnum() or len(nonce) > 32:
        return RedirectResponse(f"{destino}?erro=1", status_code=302)
    async with AsyncSessionLocal() as session, session.begin():
        row = (
            (
                await session.execute(
                    text("SELECT * FROM registrar_scan(:c, :n)"),
                    {"c": str(campanha_id), "n": nonce},
                )
            )
            .mappings()
            .first()
        )
    if row is None:
        return RedirectResponse(f"{destino}?erro=1", status_code=302)
    return RedirectResponse(f"{destino}?{urlencode(dict(row))}", status_code=302)
