from fastapi import APIRouter

from app.api.v1.aluno import treinos as aluno_treinos

api_router = APIRouter(prefix="/v1")
api_router.include_router(aluno_treinos.router)
