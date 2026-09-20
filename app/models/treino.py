import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import FocoMuscular


class Treino(Base):
    __tablename__ = "treinos"
    __table_args__ = (
        CheckConstraint(
            "minutos_disponiveis BETWEEN 15 AND 60", name="treinos_minutos_disponiveis_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    minutos_disponiveis: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    foco: Mapped[str] = mapped_column(FocoMuscular, nullable=False)
    iniciado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    concluido_em: Mapped[datetime | None] = mapped_column()


class TreinoExercicio(Base):
    __tablename__ = "treino_exercicios"
    __table_args__ = (
        UniqueConstraint("treino_id", "ordem", name="uq_treino_exercicios_treino_ordem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    treino_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treinos.id", ondelete="CASCADE"), nullable=False
    )
    exercicio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exercicios.id", ondelete="RESTRICT"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    series: Mapped[str] = mapped_column(Text, nullable=False)
    carga: Mapped[str | None] = mapped_column(Text)
    # NULL = usa o descanso padrão do exercício; o aluno pode personalizar (15-300 s).
    descanso_segundos: Mapped[int | None] = mapped_column(SmallInteger)
    concluido_em: Mapped[datetime | None] = mapped_column()


class Descanso(Base):
    __tablename__ = "descansos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    treino_exercicio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treino_exercicios.id", ondelete="CASCADE"), nullable=False
    )
    campanha_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanhas_ads.id", ondelete="SET NULL")
    )
    duracao_segundos: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    iniciado_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    pulado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class CheckIn(Base):
    __tablename__ = "check_ins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    academia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academias.id", ondelete="CASCADE"), nullable=False
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    entrada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
    saida_em: Mapped[datetime | None] = mapped_column()
