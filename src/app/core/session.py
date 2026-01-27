from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine, text

from app.core.config import settings

IS_PRODCUTION = settings.ENVIRONMENT == "production"

# Creacion del motor
# connection_args es necesario para que psycopg funcione bien con JSONB
# En produccion, ajustamos pool_size y pool_pre_ping
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    # echo = True solo en local para ver SQL logs en consola
    echo=(settings.ENVIRONMENT == "local"),
    # pool_pre_ping = True: Verifica que la conexion funcione antes de usarla
    pool_pre_ping=True,
    # pool_size: Cuantas conexiones mantenemos vivas en RAM (Default 5)
    pool_size=10,
    # max_overflow: Cuantas extra permitimos si el pool esta lleno
    max_overflow=20,
)


# Dependencia para FastAPI (The "Get DB" function)
# Esta funcion se usara en cada endpoint que necesite base de datos
# abre una session, la presta y la cierra automaticamente al terminar la peticion
def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """Crea las tablas en la BD"""
    from app.models.knowledge import KnowledgeBase  # noqa: F401

    # Esto es codigo SQL puro que indica activar pgvector
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()

    SQLModel.metadata.create_all(engine)
