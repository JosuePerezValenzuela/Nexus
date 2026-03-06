import logging
from typing import Any, TypedDict, cast

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.limiter import limiter
from app.graph.workflow import graph
from app.schemas.chat import ChatRequest, ChatResponse, ChatSafetyMeta

logger = logging.getLogger(__name__)

router = APIRouter()


class GraphResult(TypedDict, total=False):
    messages: list[Any]
    safety_meta: dict[str, object]


def _safe_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    return str(content)


@router.post("/chat", response_model=ChatResponse, response_model_exclude_none=True)
@limiter.limit("7/hour; 10/day")  # type: ignore
async def chat_with_agente(request: Request, body: ChatRequest):
    """
    Endpoint para conversar con el Workflow principal.
    """
    try:
        logger.info(f" Recibido mensaje: '{body.message}'")

        # Preparamos el input para el grafo
        # LangGraph espera un estado inicial.
        inputs = {"messages": [HumanMessage(content=body.message)]}

        # Ejecucion asincrona
        raw_result = await graph.ainvoke(inputs)  # type: ignore
        result = cast(GraphResult, raw_result)

        # 2. Extraemos el ultimo mensaje (La respuesta final del asistente)
        messages = result.get("messages", [])
        if not messages:
            logger.error("El grafo devolvio una lista de mensajes vacia.")
            raise ValueError("No response from agent")

        last_message = messages[-1]

        response_text = _safe_content(last_message.content)
        logger.info(f"Respuesta generada: {response_text[:50]}....")

        response = ChatResponse(response=response_text)
        if settings.SAFETY_GATE_ENABLED and settings.SAFETY_GATE_EXPOSE_METADATA:
            safety_meta = result.get("safety_meta")
            if isinstance(safety_meta, dict):
                response.safety = ChatSafetyMeta.model_validate(safety_meta)

        return response

    except Exception as e:
        logger.error(f"Error critico en endpoint /chat: {str(e)}", exc_info=True)
        raise HTTPException(  # noqa: B904
            status_code=500, detail="Error interno procesando la solicitud"
        )
