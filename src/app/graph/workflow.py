from typing import Any, Literal

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph  # type: ignore
from langgraph.prebuilt import create_react_agent  # type: ignore

from app.graph.nodes.supervisor import supervisor_node
from app.graph.prompt import MEDICAL_AGENT_PROMPT, PATIENT_WORKER_PROMPT
from app.graph.state import AgentState
from app.graph.tools.patients import lookup_patient_history
from app.graph.tools.rag import search_knowledge_base
from app.services.llm_service import llm_service

# --- DEFINICION DE WORKERS (SUB-GRAFOS) ---
# En lugar de nodos simples, creamos agents ReAct completos par cada especialista
# Esto asegura que ellos mismos ejecuten sus herramientas y devuelvan el resultado

# Worker 1: Especialista en Documentos (RAG)
docs_agent = create_react_agent(  # type: ignore
    model=llm_service.llm,
    tools=[search_knowledge_base],
)

# Worker 2: Especialista en Pacientes (SQL)
data_agent = create_react_agent(  # type: ignore
    model=llm_service.llm,
    tools=[lookup_patient_history],
)


# Funcion helper para invocar a los sub-agentes y formatear la salida
async def call_docs_agent(state: AgentState) -> dict[str, Any]:
    sys_msg = SystemMessage(content=MEDICAL_AGENT_PROMPT)
    inputs = {"messages": [sys_msg] + state["messages"]}
    # Invocamos al sub-grafo
    result = await docs_agent.ainvoke(inputs)  # type: ignore
    # Devolvemos el ultimo mensaje (Resp del agente)
    last_message: BaseMessage = result["messages"][-1]
    return {"messages": [last_message]}


async def call_data_agent(state: AgentState) -> dict[str, Any]:
    sys_msg = SystemMessage(content=PATIENT_WORKER_PROMPT)
    inputs = {"messages": [sys_msg] + state["messages"]}
    result = await data_agent.ainvoke(inputs)  # type: ignore
    last_message: BaseMessage = result["messages"][-1]
    return {"messages": [last_message]}


def route_supervisor(
    state: AgentState,
) -> Literal["DOCS_AGENT", "DATA_AGENT", "FINISH"]:
    """
    Función de enrutamiento segura.
    Reemplaza la lambda para evitar errores de tipo si 'next' es None.
    """
    next_node = state.get("next")

    # Mapeo de seguridad: Si el supervisor falló o mandó FINISH -> END
    if next_node == "FINISH" or not next_node:
        return "FINISH"

    # Si devuelve DOCS_AGENT o DATA_AGENT
    return next_node  # type: ignore
    # El ignore aquí es leve: Python no sabe si next_node es exactamente uno de los
    # literals, pero nosotros validamos la lógica en el nodo supervisor.


# --- CONSTRUCCION DEL GRAFO PRINCIPAL ---

# Inicializacion del grafo
workflow = StateGraph(AgentState)

# Agregamos los nodos
workflow.add_node("supervisor", supervisor_node)  # type: ignore
workflow.add_node("DOCS_AGENT", call_docs_agent)  # type: ignore
workflow.add_node("DATA_AGENT", call_data_agent)  # type: ignore

# Definimos el flujo (Edges)

# El inicio simpre va al Supervisor
workflow.add_edge(START, "supervisor")

# Router Condicional: Del supervisor a los Workers
workflow.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {"DOCS_AGENT": "DOCS_AGENT", "DATA_AGENT": "DATA_AGENT", "FINISH": END},
)

# El ciclo de retorno: Los workers SIEMPRE reportan de vuelta al supervisor
workflow.add_edge("DOCS_AGENT", "supervisor")
workflow.add_edge("DATA_AGENT", "supervisor")

# Compilacion
graph = workflow.compile()  # type: ignore
