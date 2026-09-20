"""Ponto de extensão da Fase 2: integração com Spotify Web API para a jukebox.

App "Treino Express" registrado em developer.spotify.com/dashboard. Redirect
URI de dev: `http://127.0.0.1:8000/integrations/spotify/callback` (Spotify só
aceita `127.0.0.1` como loopback, não `localhost`). Escopo previsto: Web API
para busca de faixas (preenche `faixas.provedor='spotify'` e
`faixas.provedor_id`, ver docs/04-banco-de-dados.sql) — sem Web Playback SDK
por enquanto, já que o áudio sai do sistema de som da academia, não do
navegador da TV.

Requer as variáveis `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET` em
`app/core/config.py` (adicionar quando as credenciais existirem). Nada
implementado ainda nesta fase.
"""
