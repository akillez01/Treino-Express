from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["dev", "test", "staging", "prod"] = "dev"

    # Runtime da API: role SEM privilégio de superusuário — ver comentário sobre
    # RLS + superusuário na migration 0001 (alembic/versions/sql/0001_baseline.sql).
    database_url: str = "postgresql+asyncpg://treino_app:treino_app@localhost:5434/treino_express"
    # Migrations: precisa do superusuário 'treino' (bootstrap do docker-compose)
    # para DDL (ALTER TYPE, CREATE POLICY, CREATE ROLE). Nunca usar esta URL
    # para servir requests da API.
    migrations_database_url: str = (
        "postgresql+asyncpg://treino:treino@localhost:5434/treino_express"
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "changeme-generate-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes_aluno: int = 60 * 24
    jwt_expire_minutes_gestor: int = 60 * 8
    jwt_expire_minutes_anunciante: int = 60 * 8
    jwt_expire_minutes_tela: int = 60 * 24 * 30

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
