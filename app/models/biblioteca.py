import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, SmallInteger, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlunoBibliotecaFaixa(Base):
    __tablename__ = "aluno_biblioteca_faixas"
    __table_args__ = (UniqueConstraint("aluno_id", "spotify_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    spotify_id: Mapped[str] = mapped_column(Text, nullable=False)
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    artista: Mapped[str] = mapped_column(Text, nullable=False)
    duracao_segundos: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    capa_url: Mapped[str | None] = mapped_column(Text)
    adicionada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))


class AlunoBibliotecaPlaylist(Base):
    __tablename__ = "aluno_biblioteca_playlists"
    __table_args__ = (UniqueConstraint("aluno_id", "spotify_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    aluno_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    spotify_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(Text)
    tracks_total: Mapped[int] = mapped_column(Integer, nullable=False)
    adicionada_em: Mapped[datetime] = mapped_column(server_default=text("now()"))
