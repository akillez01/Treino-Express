.PHONY: dev test lint migrate seed

dev:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

migrate:
	uv run alembic upgrade head

seed:
	uv run python scripts/seed_catalogo_exercicios.py
