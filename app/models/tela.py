import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import StatusTela


class Tela(Base):
    __tablename__ = "telas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    sala: Mapped[str] = mapped_column(Text, nullable=False)
    resolucao: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'1920x1080'"))
    # '4K7-92B' — apagado após parear.
    codigo_pareamento: Mapped[str | None] = mapped_column(Text, unique=True)
    pareada_em: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(
        StatusTela, nullable=False, server_default=text("'offline'")
    )
    ultimo_heartbeat: Mapped[datetime | None] = mapped_column()
    criada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
