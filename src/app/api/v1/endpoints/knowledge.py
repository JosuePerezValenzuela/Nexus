import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.session import get_db
from app.models.knowledge import KnowledgeBase
from app.schemas.knowledge import (
    DocumentResponse,
    KnowledgeCreate,
    KnowledgeRead,
    PDFResponse,
)
from app.services.knowledge_service import knowledge_service

logger = logging.getLogger(__name__)

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_db)]


# 1. POST
# response_model: Lo que ve el cliente (JSON filtrado)
# -> KnowledgeBase: Lo que devuelve la función internamente (Objeto DB completo)
@router.post("/", response_model=KnowledgeRead)
async def create_knowledge(
    *, session: SessionDep, item: KnowledgeCreate
) -> KnowledgeBase:  # 👈 AQUI: Especificamos que devolvemos un objeto de base de datos
    """
    Recibe un documento, lo vectoriza y lo guarda.
    """
    try:
        logger.info(f" Creando documento manual: {item.title}")
        db_obj = KnowledgeBase.model_validate(item)
        return await knowledge_service.create_new_document(session, db_obj)
    except Exception as e:
        logger.error(f"Error creando el documento: {e}")
        raise HTTPException(status_code=500, detail="Error guardando el documento")  # noqa: B904


# 2. GET
@router.get("/", response_model=list[KnowledgeRead])
async def read_knowledge(
    session: SessionDep,
) -> list[KnowledgeBase]:  # 👈 AQUI: Devolvemos una lista de objetos de BD
    """
    Obtiene todos los documentos de la base de conocimiento.
    """
    return await knowledge_service.get_all_documents(session)


# 3. Post para subir PDF
@router.post("/upload-pdf", response_model=PDFResponse)
async def upload_pdf(session: SessionDep, file: UploadFile = File(...)) -> PDFResponse:
    """
    Sube un PDF, lo divide en fragmentos y lo guarda en la base vetorial
    """
    # Validacion rapida
    if not file.filename.lower().endswith(".pdf"):  # type: ignore
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    try:
        logger.info(f" Recibiendo PDF: {file.filename}")
        return await knowledge_service.proccess_pdf(session, file)
    except Exception as e:
        logger.error(f" Error procesando PDF {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno procesando el PDF")  # noqa: B904


# 4. Post para obtener los vectores mas parecidos a lo enviado
@router.post("/search/", response_model=list[DocumentResponse])
async def search_knowledge(
    query: str,
    session: SessionDep,
    limit: int = 5,
) -> list[KnowledgeBase]:
    """
    Endpoint temporal para probar la busqueda vectorial (Recall)
    Busca los N fragmentos mas parecidos a la consulta
    """
    logger.info(f"Test de busqueda vectorial: '{query}")
    results = await knowledge_service.search_similarity(session, query, limit)

    if not results:
        logger.info(" Busqueda sin resultados")

    return results
