from langchain_core.tools import tool  # type: ignore
from pydantic import BaseModel, Field
from sqlmodel import Session  # type: ignore

from app.core.session import engine
from app.services.knowledge_service import knowledge_service


# Definicion del esquema de entrada
# Esto le dice al LLM estricto que esperar.
class SearchInput(BaseModel):
    query: str = Field(
        description="La frase de busqueda tecnica. Debe ser especifica, ej: 'Criterios diabetes' en lugar de 'diabetes'."  # noqa: E501
    )


# Decorador con args_schema
@tool(args_schema=SearchInput)
async def search_knowledge_base(query: str) -> str:
    """
    Herramienta de Busqueda Vectorial (RAG).
    Usala SIEMPRE que necesites verificar datos clinicos, normas bolivianas,
    medicamentos o protocolos medicos.

    NO la uses para saludos o preguntas de sentido comun.
    """

    # Manejo de la Sesion
    # Abrimos una sesion efimera solo para esta consulta.
    # Nota: En tools es aceptable usar el engine global porque corren aisladas
    with Session(engine) as session:
        try:
            # Llamamos al servicio
            results = await knowledge_service.search_similarity(session, query, k=3)

            if not results:
                return (
                    "No se encontro informacion relevante en la base de conocimientos."  # noqa: E501
                )

            response_text = f"Se encontraron {len(results)} documentos relevantes:\n\n"

            for i, result in enumerate(results, 1):
                # Defensive programming con getattr por si el modelo cambia
                source = getattr(result, "source", "Sistema")
                title = getattr(result, "title", "Fragmento")

                response_text += (
                    f"--- DOCUMENTO {i}---\n"
                    f" FUENTE: {source}\n"
                    f" TITULO: {title}\n"
                    f" CONTENIDO:\n{result.content.strip()}\n\n"
                )

            return response_text
        except Exception as e:
            return f" Error tecnico al consultar la base de datos: {str(e)}"
