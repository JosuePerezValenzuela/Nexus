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
    patient_context: str | None = Field(
        default=None,
        description=(
            "Resumen CORTO de datos del paciente relevantes para la busqueda"
            "(ej: 'Hombre 45 años, Glucosa 145 mg/dL')."
            "El buscador usara esto para priorizar documentos que coincidan con estos valores."  # noqa: E501
        ),
    )


# Decorador con args_schema
@tool(args_schema=SearchInput)
async def search_knowledge_base(query: str, patient_context: str | None = None) -> str:
    """
    Herramienta de Busqueda Vectorial (RAG) con Inteligencia Contextual.
    Usala para verificar guias medicas, protocolos, valores normales/anormales,
    criterios de diagnostico, cosas relacionadas a medicina.
    """

    # Abrimos sesion efimera
    with Session(engine) as session:
        try:
            # LLamamos al servicio pasando el contexto (si existe)
            results = await knowledge_service.search_similarity(
                session, query, k=4, context_summary=patient_context
            )

            if not results:
                return "No se encontro informacion relevante en las guias medicas."

            # FORMATO DE SALIDA
            # Preparacion de un string claro para que el LLM lo consuma.

            response_text = f"### Resultados de Busqueda para: '{query}'\n"
            if patient_context:
                response_text += f"(Contexto aplicado: {patient_context})"

            for i, result in enumerate(results, 1):
                # Extraemos metadatos
                source = getattr(result, "source", "Desconocido")
                title = getattr(result, "title", "Documento")

                # Obtenemos el SCRORE del RERANKER
                meta = getattr(result, "metadata", {}) or {}
                score = meta.get("relevance_score", 0.0)

                response_text += (
                    f" [Doc {i}] {title}\n"
                    f" Relevancia: {score:.2f} | Fuente: {source}\n"
                    f" CONTENIDO:\n{result.content.strip()}\n"
                    f"--- Fin del fragmento ---\n\n"
                )

                return response_text

        except Exception as e:
            return f" Error tecnico al consultar KnowledgeBase: {str(e)}"
