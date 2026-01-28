from langchain_core.messages import SystemMessage

from app.graph.prompt import MEDICAL_AGENT_PROMPT
from app.graph.state import AgentState
from app.graph.tools.rag import search_knowledge_base
from app.services.llm_service import llm_service

# Definicion de las herramienas que usara este nodo
# Cada agente podria tener tools distintas
TOOLS = [search_knowledge_base]

# Vinculacion de las herramientas al modelo
# El nodo debe ser autosuficiente
llm_with_tools = llm_service.llm.bind_tools(TOOLS)  # type: ignore


async def agent_node(state: AgentState):
    """
    Funcion del Nodo Agente.
    Responsabilidad: Orquestar la llamada al LLM con el contexto adecuado.
    """
    # Inyeccion del System Prompt
    sys_msg = SystemMessage(content=MEDICAL_AGENT_PROMPT)

    # Construccion del historial actual
    messages = [sys_msg] + state["messages"]

    # Invocamos al modelo
    response = await llm_with_tools.ainvoke(messages)

    # Retornamos solo lo nuevo (el reducer se encarga del resto)
    return {"messages": [response]}
