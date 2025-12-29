from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead
from app.services.knowledge_service import knowledge_service

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_db)]


# 1. POST
# response_model: Lo que ve el cliente (JSON filtrado)
# -> KnowledgeBase: Lo que devuelve la función internamente (Objeto DB completo)
@router.post("/", response_model=KnowledgeRead)
def create_knowledge(
    *, session: SessionDep, item: KnowledgeCreate
) -> KnowledgeBase:  # 👈 AQUI: Especificamos que devolvemos un objeto de base de datos
    """
    Recibe un documento, lo vectoriza y lo guarda.
    """
    db_obj = KnowledgeBase.model_validate(item)
    return knowledge_service.create_new_document(session, db_obj)


# 2. GET
@router.get("/", response_model=list[KnowledgeRead])
def read_knowledge(
    session: SessionDep,
) -> list[KnowledgeBase]:  # 👈 AQUI: Devolvemos una lista de objetos de BD
    """
    Obtiene todos los documentos de la base de conocimiento.
    """
    return knowledge_service.get_all_documents(session)
