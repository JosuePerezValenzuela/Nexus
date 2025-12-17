from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.session import get_db
from app.schemas.knowledge import KnowledgeCreate, KnowledgePublic
from app.services.knowledge_service import knowledge_service

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=KnowledgePublic)
def create_knowledge(item_in: KnowledgeCreate, session: SessionDep):
    """
    Endpoint limpio: Solo recibe y delega al servicio

    :param item_in: El contenido a guardar
    :type item_in: KnowledgeCreate
    :param session: Provee la session de base de datos
    :type session: Session
    """
    return knowledge_service.create_new_document(session, item_in)
