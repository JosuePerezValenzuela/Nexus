import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference  # type: ignore
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.session import create_db_and_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nexus_ai")

IS_PRODUCTION = settings.ENVIRONMENT == "production"


# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(" Nexus AI: Inicializando sistemas...")
    # Diagnostico de LangSmith
    load_dotenv()
    if not IS_PRODUCTION:
        key = os.getenv("LANGCHAIN_API_KEY")
        tracing = os.getenv("LANGCHAIN_TRACING_V2")
        if key:
            logger.info(" LangSmith key detectada")
        if tracing == "true":
            logger.info(" Tracing activado")

    # Bases de datos
    try:
        # Importacion de modelos aqui o en __init__ para que SQLModel los vea
        await create_db_and_tables()
        logger.info("Tablas de conocimiento verificadas/creadas.")
    except Exception as e:
        logger.error(f" Error conectando a BD: {e}")

    yield
    print("Nexus AI: Apagando.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    openapi_url=None if IS_PRODUCTION else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Configuracion de CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        # 1. ¿Quien puede entrar? (Lista de dominios permitidos)
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        # 2. ¿Permitir cookies/credenciales) (Generalmente True para FrontEnd)
        allow_credentials=True,
        # 3. ¿Que verbos? (GET, POST, PUT, DELETE....)
        allow_methods=["*"],
        # 4. ¿Que headers? (Auth tokens, etc)
        allow_headers=["*"],
    )

# --- RUTAS ---
app.include_router(api_router, prefix="/api/v1")


# --- Health cheack ---
@app.get("/health", tags=["Health"])
async def root() -> dict[str, str]:
    return {
        "status": "ok",
    }


if not IS_PRODUCTION:

    @app.get("/docsScalar", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
        )


def start():
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["src"]
    )


if __name__ == "__main__":
    start()
