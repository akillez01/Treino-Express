"""Integração com a Spotify Web API para a jukebox (ver client.py).

App "Treino Express" em developer.spotify.com/dashboard. Fluxo Client Credentials:
busca de faixas e metadados no servidor, sem login do aluno no Spotify. O áudio
continua saindo do sistema de som da academia (sem Web Playback SDK).

Configuração (arquivo .env): SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_MARKET.
Redirect URI de dev cadastrado no app: http://127.0.0.1:8000/integrations/spotify/callback
(só necessário se um dia houver login de usuário; o fluxo atual não o usa).
"""
