from collections.abc import Generator

from sqlmodel import Session

from app.core.session import engine  # 👈 Importamos el MOTOR global


# Esta es la función mágica
def get_db() -> Generator[Session, None, None]:
    """
    Crea una sesión nueva para cada request y la cierra al terminar.
    """
    with Session(engine) as session:
        yield session  # 1. Entrega la sesión al Endpoint
        # 2. (Pausa aquí mientras el endpoint trabaja)
        # 3. Cuando el endpoint termina, Python vuelve aquí y cierra la sesión
        # automaticamente
