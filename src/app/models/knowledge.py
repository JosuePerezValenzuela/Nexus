from datetime import UTC, datetime

from sqlmodel import Field, SQLModel  # type: ignore


def get_utc_now():
    return datetime.now(UTC)


class KnowledgeBase(SQLModel, table=True):
    # Identificador
    id: int | None = Field(default=None, primary_key=True)

    # Contenido Real (Lo que el humano lee)
    title: str = Field(index=True)
    content: str  # El texto largo que el agente leera

    # Metadatos para RAG (Vital para filtrar despues)
    # Ej: {"source": "pdf_manual", "author": "admin"}
    # En postgres esto sera un campo JSONB
    source: str | None = Field(default="user_input")

    created_at: datetime = Field(default_factory=get_utc_now)
