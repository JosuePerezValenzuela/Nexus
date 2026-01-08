from typing import Any

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.agents.rag_agent import rag_graph

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_worker(request: ChatRequest):
    """
    Endpoint para conversar con el Worker de RAG.
    El agente decidira si buscar en la BD o responder directamente
    """
    try:
        # 1. Invocamos al grafo de LangGraph
        # Usamos 'ainvoke' (asincrono) para no bloquear el servidor
        inputs = {"messages": [HumanMessage(content=request.message)]}

        result: dict[str, Any] = await rag_graph.ainvoke(inputs)  # type: ignore

        # 2. Extraemos el ultimo mensaje (La respuesta final del asistente)
        last_message = result["messages"][-1]

        return ChatResponse(response=last_message.content)

    except Exception as e:
        print(f"Error en el agente RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
