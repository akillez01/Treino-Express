"""Importa todos os modelos para que `Base.metadata` os enxergue — necessário
para o Alembic autogenerate funcionar em migrations futuras (a baseline 0001
não depende disso, é SQL puro)."""

from app.models.academia import Academia
from app.models.aluno import Aluno
from app.models.anunciante import Anunciante
from app.models.campanha import CampanhaAd
from app.models.exercicio import Exercicio
from app.models.financeiro import CreditoAnunciante, Lancamento, Repasse
from app.models.jukebox import Faixa, JukeboxPedido
from app.models.metrica import Impressao, Scan
from app.models.tela import Tela
from app.models.treino import CheckIn, Descanso, Treino, TreinoExercicio
from app.models.views import VwDesempenhoCampanha, VwReceitaMensal

__all__ = [
    "Academia",
    "Aluno",
    "Anunciante",
    "CampanhaAd",
    "Exercicio",
    "CreditoAnunciante",
    "Lancamento",
    "Repasse",
    "Faixa",
    "JukeboxPedido",
    "Impressao",
    "Scan",
    "Tela",
    "CheckIn",
    "Descanso",
    "Treino",
    "TreinoExercicio",
    "VwDesempenhoCampanha",
    "VwReceitaMensal",
]
