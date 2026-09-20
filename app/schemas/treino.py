from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

FocoLiteral = str  # validado contra o enum do Postgres na camada de serviço


class GerarTreinoIn(BaseModel):
    minutos: int = Field(ge=15, le=60)
    foco: FocoLiteral


class ExercicioOut(BaseModel):
    ordem: int
    nome: str
    series: str
    carga: str | None = None
    imagem_url: str | None = None


class TreinoOut(BaseModel):
    treino_id: UUID
    minutos: int
    foco: str
    exercicios: list[ExercicioOut]
    descanso_segundos: int


class AnuncioStubOut(BaseModel):
    campanha_id: UUID
    marca: str
    categoria: str | None = None
    desconto: str
    manchete: str
    corpo: str
    cupom: str
    qr_url: str


class IniciarDescansoIn(BaseModel):
    ordem: int


class DescansoOut(BaseModel):
    descanso_segundos: int
    campanha: AnuncioStubOut | None = None


class ExercicioConcluidoOut(BaseModel):
    ordem: int
    concluido_em: datetime
    proximo_ordem: int | None = None
    treino_concluido: bool
