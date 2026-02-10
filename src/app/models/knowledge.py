from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy import Column
from sqlmodel import Field, SQLModel  # type: ignore


def get_utc_now():
    now = datetime.now(UTC)
    return now.replace(tzinfo=None)


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

    embedding: list[float] | None = Field(default=None, sa_column=Column(Vector(1024)))
