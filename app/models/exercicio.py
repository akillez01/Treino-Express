import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import FocoMuscular


class Exercicio(Base):
    __tablename__ = "exercicios"
    __table_args__ = (
        CheckConstraint(
            "descanso_segundos BETWEEN 15 AND 300", name="exercicios_descanso_segundos_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # NULL = exercício do catálogo global da plataforma, visível a todas as academias.
    academia_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE")
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    foco: Mapped[str] = mapped_column(FocoMuscular, nullable=False)
    grupo_muscular: Mapped[str | None] = mapped_column(Text)
    series_padrao: Mapped[str] = mapped_column(Text, nullable=False)
    carga_sugerida: Mapped[str | None] = mapped_column(Text)
    descanso_segundos: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("60")
    )
    duracao_estimada_s: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("180")
    )
    equipamento: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    # Adicionada na migration baseline junto ao patch do enum (docs/07-catalogo-exercicios.md):
    # ilustração servida do object storage, ex. `exercicios/{slug}.png`.
    imagem_url: Mapped[str | None] = mapped_column(Text)
    ordem_preferencial: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("100")
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
