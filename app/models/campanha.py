import uuid
from datetime import date, datetime, time

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import StatusCampanha


class CampanhaAd(Base):
    __tablename__ = "campanhas_ads"
    __table_args__ = (
        CheckConstraint("fim IS NULL OR fim >= inicio", name="campanhas_ads_check"),
        CheckConstraint("hora_fim > hora_inicio", name="campanhas_ads_check1"),
        CheckConstraint(
            "duracao_exibicao_s BETWEEN 5 AND 120", name="campanhas_ads_duracao_exibicao_s_check"
        ),
        CheckConstraint("orcamento_centavos > 0", name="campanhas_ads_orcamento_centavos_check"),
        CheckConstraint("gasto_centavos >= 0", name="campanhas_ads_gasto_centavos_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    anunciante_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("anunciantes.id", ondelete="CASCADE"), nullable=False
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)

    desconto_rotulo: Mapped[str] = mapped_column(Text, nullable=False)
    manchete: Mapped[str] = mapped_column(Text, nullable=False)
    corpo: Mapped[str] = mapped_column(Text, nullable=False)
    cupom: Mapped[str] = mapped_column(Text, nullable=False)
    criativo_url: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        StatusCampanha, nullable=False, server_default=text("'rascunho'")
    )
    inicio: Mapped[date] = mapped_column(nullable=False)
    fim: Mapped[date | None] = mapped_column()
    hora_inicio: Mapped[time] = mapped_column(nullable=False, server_default=text("'06:00'"))
    hora_fim: Mapped[time] = mapped_column(nullable=False, server_default=text("'22:00'"))
    duracao_exibicao_s: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("24")
    )

    orcamento_centavos: Mapped[int] = mapped_column(BigInteger, nullable=False)
    gasto_centavos: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    cpm_centavos: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    limite_diario_centavos: Mapped[int | None] = mapped_column(BigInteger)
    criada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
