import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Anunciante(Base):
    __tablename__ = "anunciantes"
    __table_args__ = (CheckConstraint("saldo_centavos >= 0", name="saldo_centavos_check"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    categoria: Mapped[str | None] = mapped_column(Text)
    cnpj: Mapped[str | None] = mapped_column(Text, unique=True)
    email_contato: Mapped[str] = mapped_column(Text, nullable=False)
    telefone: Mapped[str | None] = mapped_column(Text)
    distancia_metros: Mapped[int | None] = mapped_column()
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, unique=True)
    saldo_centavos: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
