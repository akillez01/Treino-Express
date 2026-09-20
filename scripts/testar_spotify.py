"""Confere se as credenciais do Spotify no .env funcionam (busca uma música).

Uso:
    PYTHONPATH=. uv run python scripts/testar_spotify.py [termo]
"""

import asyncio
import sys

from app.integrations.spotify import client as spotify


async def main() -> int:
    if not spotify.configurado():
        print("Faltam SPOTIFY_CLIENT_ID e/ou SPOTIFY_CLIENT_SECRET no .env")
        return 1
    termo = " ".join(sys.argv[1:]) or "Charlie Brown Jr"
    try:
        faixas = await spotify.buscar_faixas(termo, 3)
    except spotify.SpotifyIndisponivel as exc:
        print(f"Falhou: {exc}")
        return 1
    print(f"OK — {len(faixas)} resultados para '{termo}':")
    for f in faixas:
        print(f"  {f.id}  {f.titulo} — {f.artista} ({f.duracao_segundos}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
