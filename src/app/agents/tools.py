from langchain_core.tools import tool  # type: ignore
from sqlmodel import Session

from app.core.session import engine
from app.services.knowledge_service import knowledge_service


@tool
async def search_knowledge_base(query: str) -> str:
    """
    Herramienta para buscar informacion especifica en la base de conocimiento interna.
    Usa esta herramienta cuando el usuario pregunte sobre informacion local (Bolivia)
    o documentos subidos
    """
    # Creacion de una sesion sincrona dedicada para la tool
    with Session(engine) as session:
        # Reutilizacion del servicio ya implementado que busca los vectores similares
        results = await knowledge_service.search_similarity(session, query, k=3)

        if not results:
            return "No se encontro informacion relevante en la base de datos."

        # Formateo de la respuesta para el agente
        response_text = "Informacion encontrada:\n\n"
        for doc in results:
            response_text += f"--- Fuente: {doc.source} ---\n{doc.content}\n\n"

        return response_text
