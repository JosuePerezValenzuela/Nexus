from fastapi import APIRouter

from app.api.v1.endpoints import knowledge  # 👈 1. Importar el archivo nuevo

api_router = APIRouter()

# 2. Incluir el router de knowledge
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
