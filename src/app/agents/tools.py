from langchain_core.tools import tool  # type: ignore
from sqlmodel import Session

from app.core.session import engine
from app.services.knowledge_service import knowledge_service


@tool
async def search_knowledge_base(query: str) -> str:
    """
    Usala para buscar informacion clinica oficial, informacion nutricional o
    lista de medicamentos

    No la uses para respuestas que no requieran de conocimiento medico

    Args:
        query: La frase exacta a buscar en los documentos.
    """
    # Creacion de una sesion sincrona dedicada para la tool
    with Session(engine) as session:
        # Reutilizacion del servicio ya implementado que busca los vectores similares
        results = await knowledge_service.search_similarity(session, query, k=3)

        if not results:
            return "No se encontro informacion relevante en la base de datos."

        # Formateo de la respuesta para el agente
        response_text = "Informacion encontrada:\n\n"
        for i, result in enumerate(results, 1):
            source = getattr(result, "source", "Desconocido")
            title = getattr(result, "title", "Sin titulo")

            response_text += (
                f"--- 📄 FRAGMENTO {i} ---\n"
                f"**Fuente:** {source}\n"
                f"**Sección:** {title}\n"
                f"**Contenido:**\n"
                f"> {result.content.strip()}\n\n"  # El '>' crea una cita bloque visual
            )

        return response_text
