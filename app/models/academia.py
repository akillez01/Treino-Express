import uuid
from datetime import datetime

from sqlalchemy import Boolean, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Academia(Base):
    __tablename__ = "academias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    unidade: Mapped[str | None] = mapped_column(Text)
    cidade: Mapped[str | None] = mapped_column(Text)
    bairro: Mapped[str | None] = mapped_column(Text)
    cnpj: Mapped[str | None] = mapped_column(Text, unique=True)
    stripe_account_id: Mapped[str | None] = mapped_column(Text, unique=True)
    charges_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    payouts_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    percentual_repasse: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, server_default=text("60.00")
    )
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    criada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
