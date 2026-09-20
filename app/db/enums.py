"""Mapeia os tipos ENUM já criados no Postgres (docs/04-banco-de-dados.sql).

`create_type=False` em todos: o tipo já existe via migration Alembic — o
SQLAlchemy nunca deve tentar criar ou dropar esses tipos.
"""

from sqlalchemy import Enum as PgEnum

PlanoAluno = PgEnum(
    "mensal",
    "trimestral",
    "anual",
    name="plano_aluno",
    create_type=False,
)

SituacaoPagamento = PgEnum(
    "em_dia",
    "pendente",
    "atrasado",
    name="situacao_pagamento",
    create_type=False,
)

# Valores originais do schema + os 4 grupos adicionados via ALTER TYPE na
# migration baseline (ver docs/07-catalogo-exercicios.md).
FocoMuscular = PgEnum(
    "cardio",
    "superiores",
    "pernas",
    "fullbody",
    "peito_triceps",
    "costas_biceps",
    "ombros",
    "bracos",
    name="foco_muscular",
    create_type=False,
)

StatusCampanha = PgEnum(
    "rascunho",
    "ativa",
    "pausada",
    "encerrada",
    name="status_campanha",
    create_type=False,
)

StatusTela = PgEnum(
    "online",
    "pausada",
    "offline",
    name="status_tela",
    create_type=False,
)

OrigemLancamento = PgEnum(
    "mensalidade",
    "anuncio",
    "jukebox",
    name="origem_lancamento",
    create_type=False,
)

StatusLancamento = PgEnum(
    "liquidado",
    "a_receber",
    "recusado",
    name="status_lancamento",
    create_type=False,
)

StatusRepasse = PgEnum(
    "pendente",
    "em_transito",
    "pago",
    "falhou",
    name="status_repasse",
    create_type=False,
)
