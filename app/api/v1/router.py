from fastapi import APIRouter

from app.api.v1 import anunciante, auth, gestor, spotify, tv
from app.api.v1.aluno import jukebox as aluno_jukebox
from app.api.v1.aluno import progresso as aluno_progresso
from app.api.v1.aluno import treinos as aluno_treinos

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(aluno_treinos.router)
api_router.include_router(aluno_jukebox.router)
api_router.include_router(aluno_progresso.router)
api_router.include_router(gestor.router)
api_router.include_router(anunciante.router)
api_router.include_router(tv.router)
api_router.include_router(spotify.router)
