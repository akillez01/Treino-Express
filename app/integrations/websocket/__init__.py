"""Ponto de extensão da Fase 2: gateway WebSocket (docs/05-api-e-websocket.md).

Vai cobrir: `WSS /ws/tv/{academia_id}?token=<jwt_da_tela>`, uma sala por
academia, heartbeat de 30s, e o consumo dos canais pub/sub `chan:tv:{academia_id}`
publicados por `treino_service.registrar_descanso` (evento `ad.show`) e pelo
worker de rotação de jukebox (`jukebox.now`, `jukebox.queue`). Nada implementado
ainda nesta fase.
"""
