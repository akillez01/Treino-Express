# Treino Express · Backend

SaaS multi-tenant para academias (FastAPI + PostgreSQL com RLS + Redis).
Design e contratos de referência: `../treino-express-handoff/`.

## Estado atual

- Schema aplicado via Alembic (baseline = SQL do handoff + enum de 6 focos + `exercicios.imagem_url`)
- Auth JWT com 4 perfis (`aluno`, `gestor`, `anunciante`, `tela`)
- Isolamento por tenant via Row Level Security
- Rotas do app do aluno: treino, progresso, metas, ranking, jukebox, biblioteca
  pessoal, playlists salvas e player Spotify persistente

Ainda não existem: workers de anúncio (pacing por verba e cobrança), Stripe Connect.

Documentação completa de arquitetura, configuração, deploy, tutorial, vantagens,
limitações e troubleshooting: [`docs/08-guia-completo.md`](docs/08-guia-completo.md).

## TV em tempo real (WebSocket)

`WSS /ws/tv/{academia_id}?token=<jwt da tela>`: anúncio (`ad.show`), jukebox (`jukebox.now`/`jukebox.queue`), `screen.pause` e heartbeat. A tela confirma cada exibição (`ad.impression`) — só assim a impressão conta. O QR do anúncio aponta para `/r/{campanha}/{nonce}` (nonce de uso único), que registra o scan e leva ao cupom.

Pareamento: painel da academia > Telas > gerar código; na TV, `/tv` e digite o código (ou `/tv?demo` com o login demo ligado).

## Spotify (jukebox)

Busca e pedido de músicas pelo aluno (`/v1/jukebox/*`), fluxo Client Credentials.

1. Em developer.spotify.com/dashboard, abra o app > Settings e copie Client ID e Client Secret.
2. Coloque no `.env` (nunca no git): `SPOTIFY_CLIENT_ID=...` e `SPOTIFY_CLIENT_SECRET=...`.
3. Confira: `PYTHONPATH=. uv run python scripts/testar_spotify.py`.
4. Teste na tela: `/aluno/jukebox`.

## Setup local

```bash
# 1. Postgres + Redis (compose do handoff)
cd ../treino-express-handoff/infra && docker compose up -d

# 2. Dependências e variáveis
cd ../../treino-express-app
uv sync
cp .env.example .env        # troque JWT_SECRET

# 3. Schema + catálogo de exercícios
uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/seed_catalogo_exercicios.py

# 4. API
make dev                    # http://127.0.0.1:8000/docs
```

Token de aluno para testes manuais:
`PYTHONPATH=. uv run python scripts/gerar_token_dev.py <academia_id> <aluno_id>`

## Duas roles de banco (importante)

| URL | Role | Uso |
| --- | --- | --- |
| `DATABASE_URL` | `treino_app` (comum) | Runtime da API — sujeita ao RLS |
| `MIGRATIONS_DATABASE_URL` | `treino` (superusuário) | Só Alembic e seeds administrativos |

Superusuário **ignora RLS sempre**, mesmo com `FORCE ROW LEVEL SECURITY`. A API nunca deve
conectar como `treino`.

## Testes

```bash
make test    # cria/migra o banco treino_express_test automaticamente
make lint
```

Rodam contra Postgres real (RLS não tem equivalente em SQLite).
