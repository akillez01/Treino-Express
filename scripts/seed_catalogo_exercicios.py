"""Popula o catálogo global de exercícios (academia_id = NULL) a partir de
docs/07-catalogo-exercicios.md. Idempotente: usa `nome` + `foco` como chave
natural e faz upsert manual (skip se já existir).

Usa a conexão de superusuário (`migrations_database_url`), não a role de
runtime da API: a policy `tenant_ou_global` em `exercicios` só permite
`WITH CHECK (academia_id = tenant_atual())`, que nunca é satisfeito para
`academia_id IS NULL` — inserir no catálogo global é deliberadamente uma
operação administrativa, fora do caminho normal da API tenant-scoped.

Uso:
    uv run python scripts/seed_catalogo_exercicios.py
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.exercicio import Exercicio

_engine = create_async_engine(settings.migrations_database_url)
_AdminSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

# (nome, foco, series, carga, slug) — ordem de cada grupo é a ordem_preferencial.
# Duplicatas entre grupos (mesmo exercício, séries diferentes) são propositais:
# o catálogo do handoff repete alguns exercícios com números distintos por grupo.
CATALOGO: dict[str, list[tuple[str, str, str, str]]] = {
    "peito_triceps": [
        ("Supino com Barra", "4x10", "Barra 40 kg", "supino-com-barra"),
        ("Crucifixo com Halteres", "3x12", "2x14 kg", "crucifixo-halteres"),
        ("Supino com Agarre Junto", "3x12", "Barra 30 kg", "supino-agarre-junto"),
        ("Pullover na Polia", "3x15", "Carga 25 kg", "pullover-polia"),
        ("Puxada de Tríceps", "3x15", "Carga 20 kg", "puxada-triceps"),
        ("Flexão do Quadril em Barra", "3x12", "Peso do corpo", "flexao-quadril-barra"),
    ],
    "costas_biceps": [
        ("Puxada Frontal", "4x10", "Carga 45 kg", "puxada-frontal"),
        ("Pegada Supinada", "3x12", "Carga 40 kg", "pegada-supinada"),
        ("Puxador Triângulo", "3x12", "Carga 38 kg", "puxador-triangulo"),
        ("Remada Baixa", "3x12", "Carga 35 kg", "remada-baixa"),
        ("Remada Curvada", "4x10", "Barra 30 kg", "remada-curvada"),
        ("Rosca Direta", "3x15", "Barra 15 kg", "rosca-direta"),
    ],
    "pernas": [
        ("Máquina Extensora", "3x12", "Carga 25 kg", "maquina-extensora"),
        ("Prensa de Pernas", "4x10", "Carga 90 kg", "prensa-de-pernas"),
        ("Máquina Flexora", "3x12", "Carga 20 kg", "maquina-flexora"),
        ("Hiperextensões", "3x15", "Peso do corpo", "hiperextensoes"),
        ("Panturrilha em Pé", "4x20", "Carga 40 kg", "panturrilha-em-pe"),
        ("Panturrilha Sentado", "3x20", "Carga 25 kg", "panturrilha-sentado"),
    ],
    "ombros": [
        ("Press Militar com Halteres", "4x10", "2x12 kg", "press-militar-halteres"),
        ("Elevações Laterais", "3x15", "2x8 kg", "elevacoes-laterais"),
        ("Encolhimento com Halteres", "4x15", "2x20 kg", "encolhimento-halteres"),
        ("Pullover na Polia", "3x15", "Carga 25 kg", "pullover-polia"),
        ("Puxada de Dorsais em Polia Alta", "3x12", "Carga 40 kg", "puxada-dorsais-polia-alta"),
        ("Remada em Polia Baixa", "3x12", "Carga 35 kg", "remada-polia-baixa"),
    ],
    "bracos": [
        ("Rosca Direta", "4x12", "Barra 18 kg", "rosca-direta"),
        ("Rosca Inclinada", "3x12", "2x10 kg", "rosca-inclinada"),
        ("Rosca Martelo na Polia", "3x15", "Carga 18 kg", "rosca-martelo-polia"),
        ("Rosca Scott", "3x12", "Barra W 15 kg", "rosca-scott"),
        ("Rosca Concentrada", "3x12", "12 kg", "rosca-concentrada"),
        ("Puxada de Tríceps", "4x15", "Carga 22 kg", "puxada-triceps"),
    ],
    "fullbody": [
        ("Prensa de Pernas", "3x12", "Carga 80 kg", "prensa-de-pernas"),
        ("Supino com Barra", "3x12", "Barra 35 kg", "supino-com-barra"),
        ("Puxada Frontal", "3x12", "Carga 40 kg", "puxada-frontal"),
        ("Press Militar com Halteres", "3x10", "2x10 kg", "press-militar-halteres"),
        ("Curl com Halteres", "3x12", "2x10 kg", "curl-halteres"),
        ("Flexão do Quadril em Barra", "3x12", "Peso do corpo", "flexao-quadril-barra"),
    ],
}

IMAGEM_URL_BASE = "/exercicios/{slug}.png"


async def seed() -> None:
    async with _AdminSessionLocal() as session:
        async with session.begin():
            inseridos = 0
            for foco, exercicios in CATALOGO.items():
                for ordem, (nome, series, carga, slug) in enumerate(exercicios, start=1):
                    existe = await session.execute(
                        select(Exercicio.id).where(
                            Exercicio.academia_id.is_(None),
                            Exercicio.nome == nome,
                            Exercicio.foco == foco,
                        )
                    )
                    if existe.scalar_one_or_none() is not None:
                        continue
                    session.add(
                        Exercicio(
                            academia_id=None,
                            nome=nome,
                            foco=foco,
                            series_padrao=series,
                            carga_sugerida=carga,
                            imagem_url=IMAGEM_URL_BASE.format(slug=slug),
                            ordem_preferencial=ordem,
                        )
                    )
                    inseridos += 1
            print(f"{inseridos} exercícios inseridos (já existentes foram ignorados).")


if __name__ == "__main__":
    asyncio.run(seed())
