from fastapi import APIRouter

from app.api.v1.endpoints import agent, knowledge, naive  # 1. Importar archivos nuevos

api_router = APIRouter()

# Incluir el router de knowledge
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])

# Inclusion de las rutas de agentes
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])

# Incluimos la ruta del naive RAG
api_router.include_router(naive.router, prefix="/naive", tags=["naive"])
