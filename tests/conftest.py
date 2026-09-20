"""Testes de API rodam contra um Postgres real (`treino_express_test`), não
SQLite — Row Level Security e `set_config('app.academia_id', ...)` não têm
equivalente fiel fora do Postgres.

As variáveis de ambiente são sobrescritas ANTES de qualquer `import app...`
(o singleton `settings` em app.core.config é montado na primeira importação),
então este bloco tem que ficar no topo do arquivo, antes dos outros imports.
"""

import os
import uuid

TEST_DB_NAME = "treino_express_test"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-32-bytes-min"
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://treino_app:treino_app@localhost:5434/{TEST_DB_NAME}"
)
os.environ["MIGRATIONS_DATABASE_URL"] = (
    f"postgresql+asyncpg://treino:treino@localhost:5434/{TEST_DB_NAME}"
)

import asyncio  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADMIN_BOOTSTRAP_URL = "postgresql://treino:treino@localhost:5434/postgres"


async def _ensure_test_database() -> None:
    conn = await asyncpg.connect(ADMIN_BOOTSTRAP_URL)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


def _run_migrations() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        check=True,
        env=os.environ,
    )


@pytest.fixture(scope="session", autouse=True)
def test_database_ready():
    asyncio.run(_ensure_test_database())
    _run_migrations()
    yield


@pytest.fixture(scope="session")
def admin_sessionmaker():
    """Sessão via superusuário (bypassa RLS) — só para preparar fixtures de
    teste (academias, alunos, exercícios), nunca para exercitar o código sob
    teste (isso é feito pelo `client`, que passa pela role restrita)."""
    from app.core.config import settings

    engine = create_async_engine(settings.migrations_database_url)
    yield async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def _seed_catalogo_global(test_database_ready, admin_sessionmaker):
    """Seis exercícios por foco (o máximo que `calcular_qtd_exercicios` pede),
    idempotente entre execuções — o banco de teste persiste entre runs."""
    from sqlalchemy import func, select

    from app.models.exercicio import Exercicio

    focos = ["pernas", "peito_triceps", "costas_biceps", "ombros", "bracos", "fullbody"]
    async with admin_sessionmaker() as session:
        async with session.begin():
            for foco in focos:
                existentes = await session.scalar(
                    select(func.count())
                    .select_from(Exercicio)
                    .where(Exercicio.academia_id.is_(None), Exercicio.foco == foco)
                )
                for ordem in range(existentes or 0, 6):
                    session.add(
                        Exercicio(
                            academia_id=None,
                            nome=f"Exercício de teste {ordem + 1} ({foco})",
                            foco=foco,
                            series_padrao="3x12",
                            carga_sugerida="10 kg",
                            ordem_preferencial=ordem + 1,
                        )
                    )


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def duas_academias(admin_sessionmaker):
    """Cria duas academias com um aluno cada, com IDs únicos por execução de
    teste — evita qualquer necessidade de truncar tabelas entre testes (o que
    exigiria cuidado extra para não arrastar o catálogo global de exercícios
    via CASCADE)."""
    from app.models.academia import Academia
    from app.models.aluno import Aluno

    suffix = uuid.uuid4().hex[:8]
    async with admin_sessionmaker() as session:
        async with session.begin():
            academia_a = Academia(nome="Academia A", slug=f"academia-a-{suffix}")
            academia_b = Academia(nome="Academia B", slug=f"academia-b-{suffix}")
            session.add_all([academia_a, academia_b])
            await session.flush()

            aluno_a = Aluno(
                academia_id=academia_a.id,
                nome="Aluno A",
                email=f"aluno-a-{suffix}@teste.com",
                mensalidade_centavos=10000,
            )
            aluno_b = Aluno(
                academia_id=academia_b.id,
                nome="Aluno B",
                email=f"aluno-b-{suffix}@teste.com",
                mensalidade_centavos=10000,
            )
            session.add_all([aluno_a, aluno_b])
            await session.flush()

            academia_a_id, academia_b_id = academia_a.id, academia_b.id
            aluno_a_id, aluno_b_id = aluno_a.id, aluno_b.id

    token_a = create_access_token(
        subject=str(aluno_a_id), type="aluno", academia_id=academia_a_id, aluno_id=aluno_a_id
    )
    token_b = create_access_token(
        subject=str(aluno_b_id), type="aluno", academia_id=academia_b_id, aluno_id=aluno_b_id
    )
    return {
        "academia_a": academia_a_id,
        "academia_b": academia_b_id,
        "aluno_a": aluno_a_id,
        "aluno_b": aluno_b_id,
        "token_a": token_a,
        "token_b": token_b,
    }
