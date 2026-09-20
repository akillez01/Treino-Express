"""Cliente da Spotify Web API (fluxo Client Credentials).

Cobre só o que a jukebox precisa: buscar faixas e ler os metadados de uma faixa
(título, artista, duração, capa). Não toca áudio nem acessa conta de usuário.
"""

import time
from dataclasses import dataclass

import httpx

from app.core.config import settings

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"


class SpotifyNaoConfigurado(Exception):
    pass


class SpotifyIndisponivel(Exception):
    pass


@dataclass(frozen=True)
class Faixa:
    id: str
    titulo: str
    artista: str
    duracao_segundos: int
    capa_url: str | None
    explicita: bool

    def dict(self) -> dict:
        return self.__dict__.copy()


_token: tuple[str, float] | None = None  # (access_token, expira_em monotonic)


def configurado() -> bool:
    return bool(settings.spotify_client_id and settings.spotify_client_secret)


async def _access_token(http: httpx.AsyncClient) -> str:
    global _token
    if _token and _token[1] > time.monotonic() + 30:
        return _token[0]
    if not configurado():
        raise SpotifyNaoConfigurado("SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET não definidos")
    resp = await http.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(settings.spotify_client_id, settings.spotify_client_secret),
    )
    if resp.status_code != 200:
        raise SpotifyIndisponivel(f"Spotify recusou as credenciais ({resp.status_code})")
    corpo = resp.json()
    _token = (corpo["access_token"], time.monotonic() + int(corpo.get("expires_in", 3600)))
    return _token[0]


def _faixa(item: dict) -> Faixa:
    capas = item.get("album", {}).get("images", [])
    # imagens vêm da maior para a menor; a do meio (~300px) basta para a TV/app
    capa = capas[1]["url"] if len(capas) > 1 else (capas[0]["url"] if capas else None)
    return Faixa(
        id=item["id"],
        titulo=item["name"],
        artista=", ".join(a["name"] for a in item.get("artists", [])),
        duracao_segundos=round(item["duration_ms"] / 1000),
        capa_url=capa,
        explicita=bool(item.get("explicit")),
    )


async def _get(caminho: str, params: dict | None = None, *, http: httpx.AsyncClient | None = None):
    proprio = http is None
    http = http or httpx.AsyncClient(timeout=8)
    try:
        token = await _access_token(http)
        resp = await http.get(
            f"{API_URL}{caminho}", params=params, headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 401:  # token expirou antes do previsto
            global _token
            _token = None
            token = await _access_token(http)
            resp = await http.get(
                f"{API_URL}{caminho}", params=params, headers={"Authorization": f"Bearer {token}"}
            )
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise SpotifyIndisponivel(f"Spotify respondeu {resp.status_code}")
        return resp.json()
    except httpx.HTTPError as exc:
        raise SpotifyIndisponivel("Não foi possível falar com o Spotify") from exc
    finally:
        if proprio:
            await http.aclose()


async def buscar_faixas(termo: str, limite: int = 10) -> list[Faixa]:
    dados = await _get(
        "/search",
        {"q": termo, "type": "track", "limit": limite, "market": settings.spotify_market},
    )
    itens = (dados or {}).get("tracks", {}).get("items", [])
    return [_faixa(i) for i in itens if i]


async def obter_faixa(spotify_id: str) -> Faixa | None:
    dados = await _get(f"/tracks/{spotify_id}", {"market": settings.spotify_market})
    return _faixa(dados) if dados else None
