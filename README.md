# Treino Express · Backend

SaaS multi-tenant para academias (FastAPI + PostgreSQL com RLS + Redis).
Design e contratos de referência: `../treino-express-handoff/`.

## Estado atual (Fase 1 · fundação)

- Schema aplicado via Alembic (baseline = SQL do handoff + enum de 6 focos + `exercicios.imagem_url`)
- Auth JWT com 4 perfis (`aluno`, `gestor`, `anunciante`, `tela`)
- Isolamento por tenant via Row Level Security
- Rotas do app do aluno: `POST /v1/treinos/gerar`, `/v1/treinos/{id}/descanso`, `/v1/treinos/{id}/exercicio/{ordem}/concluir`

Ainda não existem: gateway WebSocket, workers de anúncio, Stripe Connect, Spotify (jukebox), frontends.

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
