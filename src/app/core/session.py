from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings

IS_PRODCUTION = settings.ENVIRONMENT == "production"

database_url = str(settings.SQLALCHEMY_DATABASE_URI)

# Creacion del motor
# connection_args es necesario para que psycopg funcione bien con JSONB
# En produccion, ajustamos pool_size y pool_pre_ping
engine: AsyncEngine = create_async_engine(
    database_url,
    # echo = True solo en local para ver SQL logs en consola
    echo=(settings.ENVIRONMENT == "local"),
    # pool_pre_ping = True: Verifica que la conexion funcione antes de usarla
    pool_pre_ping=True,
    # pool_size: Cuantas conexiones mantenemos vivas en RAM (Default 5)
    pool_size=10,
    # max_overflow: Cuantas extra permitimos si el pool esta lleno
    max_overflow=20,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


# Dependencia para FastAPI (The "Get DB" function)
# Esta funcion se usara en cada endpoint que necesite base de datos
# abre una session, la presta y la cierra automaticamente al terminar la peticion
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_db_and_tables() -> None:
    """Crea las tablas en la BD"""
    from app.db.init_data import init_db
    from app.models.knowledge import KnowledgeBase  # noqa: F401
    from app.models.patient import Patient  # noqa: F401

    # Esto es codigo SQL puro que indica activar pgvector
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session_factory() as session:
        await init_db(session)
