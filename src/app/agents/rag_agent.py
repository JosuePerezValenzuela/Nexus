from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import SystemMessage
from langgraph.graph import START, StateGraph  # type: ignore
from langgraph.graph.message import add_messages  # type: ignore
from langgraph.prebuilt import ToolNode

from app.agents.tools import search_knowledge_base
from app.services.llm_service import llm_service


# 1. Estado
class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]


SYSTEM_PROMPT = """Eres Nexus AI, un asistente experto y servicial.

TIENES DOS MODOS DE OPERACIÓN:

MODO 1: CHARLA CASUAL (Sin Herramientas)
- Si es una charla general.
-> EN ESTOS CASOS: Responde directamente y NO uses ninguna herramienta.

MODO 2: BÚSQUEDA DE INFORMACIÓN (Con Herramientas)
- Si el usuario pregunta sobre manuales, PDFs subidos o datos específicos de Bolivia.
- Si la respuesta requiere datos exactos que no conoces de memoria.
-> EN ESTOS CASOS: Usa 'search_knowledge_base', y cita las fuentes de donde sacaste la
informacion.

IMPORTANTE:
- Si usas la herramienta, cita la fuente.
- Si no encuentras nada, dilo honestamente, no inventes.
"""

# 2. Herramientas
tools = [search_knowledge_base]
tool_node = ToolNode(tools)

# 3. Modelo con herramientas vinculadas
model_with_tools = llm_service.llm.bind_tools(tools)  # type: ignore


# 4. Nodos
def agent_node(state: AgentState):
    current_messages = state["messages"]

    messages_with_rules = [SystemMessage(content=SYSTEM_PROMPT)] + current_messages

    response = model_with_tools.invoke(messages_with_rules)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"


# 5. Grafo
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)  # type: ignore
workflow.add_node("tools", tool_node)  # type: ignore

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

rag_graph = workflow.compile()  # type: ignore
