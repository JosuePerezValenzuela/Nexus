import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference  # type: ignore

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.session import create_db_and_tables

IS_PRODUCTION = settings.ENVIRONMENT == "production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Nexus AI: Inicializando memorias...")
    create_db_and_tables()
    print("Tablas de conocimiento listas.")
    yield
    print("Nexus AI: Apagando.")


load_dotenv()

print("--- DIAGNÓSTICO LANGSMITH ---")
key = os.getenv("LANGCHAIN_API_KEY")
tracing = os.getenv("LANGCHAIN_TRACING_V2")

if key:
    print(f"✅ API Key cargada: {key[:5]}...")  # Solo muestra el inicio por seguridad
else:
    print("❌ ERROR: No se encontró LANGCHAIN_API_KEY")

if tracing == "true":
    print("✅ Tracing activado")
else:
    print(f"❌ Tracing NO activo (Valor: {tracing})")
print("-----------------------------")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    openapi_url=None if IS_PRODUCTION else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
)

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

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
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
