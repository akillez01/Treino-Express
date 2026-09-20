import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import OrigemLancamento, StatusLancamento, StatusRepasse


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    origem: Mapped[str] = mapped_column(OrigemLancamento, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    valor_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        StatusLancamento, nullable=False, server_default=text("'a_receber'")
    )
    # primeiro dia do mês de referência
    competencia: Mapped[date] = mapped_column(nullable=False)
    aluno_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="SET NULL")
    )
    campanha_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanhas_ads.id", ondelete="SET NULL")
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    liquidado_em: Mapped[datetime | None] = mapped_column()


class Repasse(Base):
    __tablename__ = "repasses"
    __table_args__ = (
        CheckConstraint("bruto_centavos > 0", name="repasses_bruto_centavos_check"),
        CheckConstraint("taxa_centavos >= 0", name="repasses_taxa_centavos_check"),
        CheckConstraint("liquido_centavos >= 0", name="repasses_liquido_centavos_check"),
        CheckConstraint("bruto_centavos = taxa_centavos + liquido_centavos", name="repasses_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    anunciante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("anunciantes.id", ondelete="CASCADE"), nullable=False
    )
    campanha_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanhas_ads.id", ondelete="SET NULL")
    )
    bruto_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    taxa_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    liquido_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        StatusRepasse, nullable=False, server_default=text("'pendente'")
    )
    stripe_transfer_id: Mapped[str | None] = mapped_column(Text, unique=True)
    competencia: Mapped[date] = mapped_column(nullable=False)
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    pago_em: Mapped[datetime | None] = mapped_column()


class CreditoAnunciante(Base):
    __tablename__ = "creditos_anunciante"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    anunciante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("anunciantes.id", ondelete="CASCADE"), nullable=False
    )
    # positivo = recarga, negativo = consumo
    valor_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(Text)
    nota_fiscal: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
