"""Cliente da Spotify Web API (fluxo Client Credentials).

Cobre só o que a jukebox precisa: buscar faixas e playlists e ler metadados
(título, artista, duração, capa). Não toca áudio nem acessa conta de usuário.
"""

import re
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


@dataclass(frozen=True)
class Playlist:
    id: str
    name: str
    owner: str
    cover_url: str | None
    tracks_total: int

    def dict(self) -> dict:
        return self.__dict__.copy()


_token: tuple[str, float] | None = None  # (access_token, expira_em monotonic)
_SPOTIFY_ID = re.compile(r"^[A-Za-z0-9]{22}$")


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


def _faixa(item: object) -> Faixa | None:
    if not isinstance(item, dict):
        return None
    spotify_id = item.get("id")
    titulo = item.get("name")
    duracao_ms = item.get("duration_ms")
    if not isinstance(spotify_id, str) or not _SPOTIFY_ID.fullmatch(spotify_id):
        return None
    if not isinstance(titulo, str) or not titulo.strip():
        return None
    if not isinstance(duracao_ms, (int, float)) or duracao_ms < 0:
        return None

    artistas = item.get("artists")
    nomes = []
    if isinstance(artistas, list):
        nomes = [
            a["name"]
            for a in artistas
            if isinstance(a, dict) and isinstance(a.get("name"), str) and a["name"]
        ]
    if not nomes:
        return None

    album = item.get("album")
    imagens = album.get("images", []) if isinstance(album, dict) else []
    capas = [i.get("url") for i in imagens if isinstance(i, dict) and isinstance(i.get("url"), str)]
    # imagens vêm da maior para a menor; a do meio (~300px) basta para a TV/app
    capa = capas[1] if len(capas) > 1 else (capas[0] if capas else None)
    return Faixa(
        id=spotify_id,
        titulo=titulo,
        artista=", ".join(nomes),
        duracao_segundos=round(duracao_ms / 1000),
        capa_url=capa,
        explicita=bool(item.get("explicit")),
    )


def _playlist(item: object) -> Playlist | None:
    if not isinstance(item, dict):
        return None
    playlist_id = item.get("id")
    name = item.get("name")
    if not isinstance(playlist_id, str) or not _SPOTIFY_ID.fullmatch(playlist_id):
        return None
    if not isinstance(name, str) or not name.strip():
        return None

    owner_data = item.get("owner")
    owner = ""
    if isinstance(owner_data, dict):
        owner = owner_data.get("display_name") or owner_data.get("id") or ""
    if not isinstance(owner, str):
        owner = ""

    tracks_data = item.get("tracks")
    total = tracks_data.get("total", 0) if isinstance(tracks_data, dict) else 0
    tracks_total = int(total) if isinstance(total, (int, float)) and total >= 0 else 0
    imagens = item.get("images")
    capas = (
        [i.get("url") for i in imagens if isinstance(i, dict) and isinstance(i.get("url"), str)]
        if isinstance(imagens, list)
        else []
    )
    cover_url = capas[0] if capas else None
    return Playlist(
        id=playlist_id,
        name=name,
        owner=owner,
        cover_url=cover_url,
        tracks_total=tracks_total,
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
    tracks = dados.get("tracks") if isinstance(dados, dict) else None
    itens = tracks.get("items", []) if isinstance(tracks, dict) else []
    if not isinstance(itens, list):
        return []
    return [faixa for item in itens if (faixa := _faixa(item)) is not None]


async def obter_faixa(spotify_id: str) -> Faixa | None:
    dados = await _get(f"/tracks/{spotify_id}", {"market": settings.spotify_market})
    return _faixa(dados)


async def buscar_playlists(query: str, limite: int = 10) -> list[Playlist]:
    dados = await _get(
        "/search",
        {
            "q": query,
            "type": "playlist",
            "limit": max(1, min(limite, 50)),
            "market": settings.spotify_market,
        },
    )
    playlists = dados.get("playlists") if isinstance(dados, dict) else None
    itens = playlists.get("items", []) if isinstance(playlists, dict) else []
    if not isinstance(itens, list):
        return []
    return [playlist for item in itens if (playlist := _playlist(item)) is not None]


async def obter_playlist(spotify_id: str) -> Playlist | None:
    if not _SPOTIFY_ID.fullmatch(spotify_id):
        raise ValueError("ID de playlist Spotify inválido")
    dados = await _get(f"/playlists/{spotify_id}", {"market": settings.spotify_market})
    return _playlist(dados)


async def obter_faixas_playlist(playlist_id: str, limite: int = 30) -> list[Faixa]:
    if not _SPOTIFY_ID.fullmatch(playlist_id):
        raise ValueError("ID de playlist Spotify inválido")
    dados = await _get(
        f"/playlists/{playlist_id}/tracks",
        {"limit": max(1, min(limite, 50)), "market": settings.spotify_market},
    )
    itens = dados.get("items", []) if isinstance(dados, dict) else []
    if not isinstance(itens, list):
        return []
    faixas = []
    for item in itens:
        track = item.get("track") if isinstance(item, dict) else None
        faixa = _faixa(track)
        if faixa is not None:
            faixas.append(faixa)
    return faixas
