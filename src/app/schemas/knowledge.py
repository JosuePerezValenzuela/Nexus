from datetime import datetime

from sqlmodel import SQLModel


class KnowledgeCreate(SQLModel):
    title: str
    content: str
    source: str = "user_input"


# Tu clase de respuesta (puedes llamarla Public o Read, como prefieras)
class KnowledgeRead(SQLModel):
    id: int
    title: str
    content: str
    source: str
    created_at: datetime
