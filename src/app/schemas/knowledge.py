from pydantic import BaseModel


# Este modulo define que esperamos recibir del frontend
class KnowledgeCreate(BaseModel):
    title: str
    content: str
    source: str = "user_input"


# Este modelo define que le devolvemos la usuario (Respuesta)
class KnowledgePublic(KnowledgeCreate):
    id: int
    created_at: str  # La fecha como string
