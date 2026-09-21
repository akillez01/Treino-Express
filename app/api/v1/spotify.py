"""OAuth PKCE do Spotify para o player oficial no navegador."""

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/spotify", tags=["spotify"])

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyConfigOut(BaseModel):
    client_id: str
    authorize_url: str
    redirect_uri: str
    scopes: str
    configured: bool


class SpotifyTokenIn(BaseModel):
    code: str = Field(min_length=1, max_length=4096)
    code_verifier: str = Field(min_length=43, max_length=128)
    redirect_uri: str = Field(min_length=1, max_length=2048)


class SpotifyRefreshIn(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class SpotifyTokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str


def _validate_redirect(redirect_uri: str) -> None:
    if redirect_uri != settings.spotify_redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri não corresponde ao configurado no servidor",
        )


def _spotify_error(response: httpx.Response, action: str) -> HTTPException:
    # O corpo pode conter dados que não devem ser refletidos em logs/respostas.
    if response.status_code in {400, 401}:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spotify recusou {action}. Verifique o código e o redirect_uri.",
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Não foi possível concluir {action} com o Spotify.",
    )


def _token_response(body: Any) -> SpotifyTokenOut:
    if not isinstance(body, dict) or not isinstance(body.get("access_token"), str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta inválida do Spotify ao obter o token.",
        )
    expires_in = body.get("expires_in")
    if not isinstance(expires_in, int) or expires_in <= 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta inválida do Spotify ao obter a validade do token.",
        )
    token_type = body.get("token_type")
    if not isinstance(token_type, str) or not token_type:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta inválida do Spotify ao obter o tipo do token.",
        )
    refresh_token = body.get("refresh_token")
    return SpotifyTokenOut(
        access_token=body["access_token"],
        refresh_token=refresh_token if isinstance(refresh_token, str) else None,
        expires_in=expires_in,
        token_type=token_type,
    )


def _parse_token_response(response: httpx.Response) -> SpotifyTokenOut:
    try:
        body = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta inválida do Spotify ao obter o token.",
        ) from exc
    return _token_response(body)


@router.get("/config", response_model=SpotifyConfigOut)
async def spotify_config() -> SpotifyConfigOut:
    return SpotifyConfigOut(
        client_id=settings.spotify_client_id,
        authorize_url=AUTHORIZE_URL,
        redirect_uri=settings.spotify_redirect_uri,
        scopes=settings.spotify_scopes,
        configured=bool(settings.spotify_client_id and settings.spotify_redirect_uri),
    )


@router.post("/token", response_model=SpotifyTokenOut)
async def spotify_token(body: SpotifyTokenIn) -> SpotifyTokenOut:
    _validate_redirect(body.redirect_uri)
    if not settings.spotify_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spotify não está configurado no servidor.",
        )
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            response = await http.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": body.code,
                    "redirect_uri": body.redirect_uri,
                    "client_id": settings.spotify_client_id,
                    "code_verifier": body.code_verifier,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar ao Spotify para trocar o código.",
        ) from exc
    if response.status_code != 200:
        raise _spotify_error(response, "a autorização")
    return _parse_token_response(response)


@router.post("/refresh", response_model=SpotifyTokenOut)
async def spotify_refresh(body: SpotifyRefreshIn) -> SpotifyTokenOut:
    if not settings.spotify_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spotify não está configurado no servidor.",
        )
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            response = await http.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": body.refresh_token,
                    "client_id": settings.spotify_client_id,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível conectar ao Spotify para renovar o token.",
        ) from exc
    if response.status_code != 200:
        raise _spotify_error(response, "a renovação do token")
    return _parse_token_response(response)
