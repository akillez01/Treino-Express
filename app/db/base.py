from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base. Tabelas mapeiam o schema já existente em
    docs/04-banco-de-dados.sql — nunca deixar o SQLAlchemy criar/dropar
    tipos ou tabelas em produção; isso é responsabilidade do Alembic."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Todo TIMESTAMPTZ do schema (docs/04-banco-de-dados.sql) — sem isto,
    # `Mapped[datetime]` mapeia por padrão para TIMESTAMP WITHOUT TIME ZONE, e
    # o asyncpg rejeita valores tz-aware (datetime.now(timezone.utc)) contra
    # uma coluna naive.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }
