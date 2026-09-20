"""Views de apoio aos painéis (docs/04-banco-de-dados.sql). Mapeadas como
classes read-only — nunca fazer INSERT/UPDATE/DELETE nelas, e excluídas do
autogenerate do Alembic via `include_object` em `alembic/env.py`."""

from datetime import date
from uuid import UUID as PyUUID

from sqlalchemy import BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VwDesempenhoCampanha(Base):
    __tablename__ = "vw_desempenho_campanha"
    __table_args__ = {"info": {"is_view": True}}

    campanha_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    academia_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True))
    nome: Mapped[str] = mapped_column(Text)
    impressoes: Mapped[int] = mapped_column(BigInteger)
    scans: Mapped[int] = mapped_column(BigInteger)
    resgates: Mapped[int] = mapped_column(BigInteger)
    gasto_centavos: Mapped[int] = mapped_column(BigInteger)


class VwReceitaMensal(Base):
    __tablename__ = "vw_receita_mensal"
    __table_args__ = {"info": {"is_view": True}}

    academia_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    competencia: Mapped[date] = mapped_column(primary_key=True)
    origem: Mapped[str] = mapped_column(Text, primary_key=True)
    liquidado_centavos: Mapped[int | None] = mapped_column(BigInteger)
    a_receber_centavos: Mapped[int | None] = mapped_column(BigInteger)
