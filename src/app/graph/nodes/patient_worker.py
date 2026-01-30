from langchain_core.messages import SystemMessage

from app.graph.prompt import PATIENT_WORKER_PROMPT
from app.graph.state import AgentState
from app.graph.tools.patients import lookup_patient_history
from app.services.llm_service import llm_service

# Definicion de las herramientas de este especialista
tools = [lookup_patient_history]

# Bind del LLM con las tools
llm_with_tools = llm_service.llm.bind_tools(tools)  # type: ignore

# Prompt del especialista
SYSTEM_PROMPT = PATIENT_WORKER_PROMPT


async def patient_worker_node(state: AgentState):
    """
    Nodo que ejecuta el Agente de Datos.
    """
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    # Invocamos al LLM
    response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response]}
