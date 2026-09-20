from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import BigInteger, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Impressao(Base):
    __tablename__ = "impressoes"
    __table_args__ = (
        UniqueConstraint("campanha_id", "nonce", name="uq_impressoes_campanha_nonce"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    academia_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    campanha_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanhas_ads.id", ondelete="CASCADE"), nullable=False
    )
    tela_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("telas.id", ondelete="CASCADE"), nullable=False
    )
    descanso_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("descansos.id", ondelete="SET NULL")
    )
    # vai no QR, amarra o scan à exibição
    nonce: Mapped[str] = mapped_column(Text, nullable=False)
    custo_centavos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    exibida_em: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    academia_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    impressao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("impressoes.id", ondelete="CASCADE"), nullable=False
    )
    aluno_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="SET NULL")
    )
    escaneado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    # preenchido quando o cupom é usado na loja
    resgatado_em: Mapped[datetime | None] = mapped_column()
    valor_compra_centavos: Mapped[int | None] = mapped_column(Integer)
