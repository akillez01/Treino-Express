import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Faixa(Base):
    __tablename__ = "faixas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    artista: Mapped[str] = mapped_column(Text, nullable=False)
    duracao_segundos: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    capa_url: Mapped[str | None] = mapped_column(Text)
    # 'spotify', 'local' — ver app/integrations/spotify para o provedor 'spotify'
    provedor: Mapped[str | None] = mapped_column(Text)
    provedor_id: Mapped[str | None] = mapped_column(Text)
    liberada: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class JukeboxPedido(Base):
    __tablename__ = "jukebox_pedidos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    faixa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("faixas.id", ondelete="CASCADE"), nullable=False
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    pedido_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    tocado_em: Mapped[datetime | None] = mapped_column()
    # pedido avulso pago
    valor_centavos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
