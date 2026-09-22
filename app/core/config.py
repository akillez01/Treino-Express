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
    # Aceita também qualquer túnel temporário da Cloudflare e o app na Vercel.
    cors_origin_regex: str = (
        r"(https://.*\.(trycloudflare\.com|vercel\.app))|(http://(localhost|127\.0\.0\.1)(:\d+)?)"
    )

    # Login de demonstração: emite token só do aluno demo abaixo, enquanto o
    # login real não existe. Desligado por padrão; nunca ligar em produção.
    enable_demo_login: bool = False
    demo_academia_id: str = "11111111-1111-1111-1111-111111111111"
    demo_aluno_id: str = "22222222-2222-2222-2222-222222222222"
    demo_anunciante_id: str = "55555555-5555-5555-5555-555555555555"
    demo_tela_id: str = "a1000000-0000-0000-0000-000000000001"

    # Google Identity Services (login da conta Treino Express, não do Spotify).
    google_client_id: str = ""
    google_allowed_hosted_domain: str = ""
    google_login_enabled: bool = False
    # Como o RLS exige um tenant antes de consultar alunos, o MVP faz a busca
    # somente nesta academia explicitamente configurada. Nunca usa a role de
    # migrations para fazer uma busca global.
    google_default_academia_id: str = ""

    # Endereço público da API (vai dentro do QR) e do frontend (destino do scan).
    public_api_url: str = "http://127.0.0.1:8000"
    public_web_url: str = "http://127.0.0.1:3000"

    # Spotify Web API (app em developer.spotify.com/dashboard). O secret fica
    # somente no backend e nunca é enviado ao navegador.
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_market: str = "BR"
    spotify_redirect_uri: str = "http://localhost:3000/aluno/spotify/callback"
    spotify_scopes: str = "streaming user-read-email user-read-private"

    # WhatsApp Business Cloud API (Meta) — lembretes de sequência. Vazio = simulado.
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_template: str = "lembrete_sequencia"


settings = Settings()
