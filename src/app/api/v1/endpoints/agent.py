import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.core.limiter import limiter
from app.graph.workflow import graph

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
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
        result: dict[str, Any] = await graph.ainvoke(inputs)  # type: ignore

        # 2. Extraemos el ultimo mensaje (La respuesta final del asistente)
        messages = result.get("messages", [])
        if not messages:
            logger.error("El grafo devolvio una lista de mensajes vacia.")
            raise ValueError("No response from agent")

        last_message = messages[-1]

        logger.info(f"Respuesta generada: {last_message.content[:50]}....")

        return ChatResponse(response=last_message.content)

    except Exception as e:
        logger.error(f"Error critico en endpoint /chat: {str(e)}", exc_info=True)
        raise HTTPException(  # noqa: B904
            status_code=500, detail="Error interno procesando la solicitud"
        )
