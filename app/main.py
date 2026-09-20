from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ws
from app.api.v1.router import api_router
from app.api.v1.tv import scan_router
from app.core.config import settings

app = FastAPI(title="Treino Express API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(scan_router)
app.include_router(ws.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
