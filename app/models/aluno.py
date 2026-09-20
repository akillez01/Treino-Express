import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import PlanoAluno, SituacaoPagamento


class Aluno(Base):
    __tablename__ = "alunos"
    __table_args__ = (UniqueConstraint("academia_id", "email", name="uq_alunos_academia_email"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    telefone: Mapped[str | None] = mapped_column(Text)
    plano: Mapped[str] = mapped_column(PlanoAluno, nullable=False, server_default=text("'mensal'"))
    mensalidade_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    situacao: Mapped[str] = mapped_column(
        SituacaoPagamento, nullable=False, server_default=text("'em_dia'")
    )
    matriculado_em: Mapped[date] = mapped_column(server_default=text("CURRENT_DATE"))
    cancelado_em: Mapped[date | None] = mapped_column()
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
