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


# Definir el Prompt del Sistema optimizado
SYSTEM_PROMPT = """Eres "Nexus Health", un asistente de apoyo clínico diseñado Bolivia.
Tu objetivo es ayudar a profesionales de salud y pacientes a interpretar guías médicas
consultas y datos nutricionales locales.

INFORMACIÓN DE CONTEXTO:
1. Basas tus respuestas EXCLUSIVAMENTE en:
   - Documentos clinicos cargados en el RAG del sistema.
2. Si la información no está en los documentos RAG, DI QUE NO LO SABES. No inventes.

REGLAS DE COMPORTAMIENTO (ESTRICTAS):
- Tono: Profesional, empático y directo. Evita la verborrea ("mucho texto").
- Formato: Usa listas (bullets) para instrucciones claras.
- Idioma: Español neutro, adaptado al contexto boliviano.

LIMITACIONES DE SEGURIDAD:
- NO DIAGNOSTIQUES: Nunca digas "Tienes diabetes". Di "Los síntomas sugieren riesgo 
de diabetes según ...".
- NO RECETES: Nunca indiques dosis, Di "Consulte a su médico para la dosificación".
- Siempre finaliza con: "Recuerda: Esta información es referencial 
y no reemplaza la consulta médica."

HERRAMIENTAS:
Tienes acceso a una base de conocimientos (search_knowledge_base). 
Úsala SIEMPRE que te pregunten sobre síntomas, tratamientos, dietas o protocolos.
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
