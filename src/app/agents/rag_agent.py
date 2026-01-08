from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import START, StateGraph  # type: ignore
from langgraph.graph.message import add_messages  # type: ignore
from langgraph.prebuilt import ToolNode

from app.agents.tools import search_knowledge_base
from app.services.llm_service import llm_service


# 1. Estado
class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]


# 2. Herramientas
tools = [search_knowledge_base]
tool_node = ToolNode(tools)

# 3. Modelo con herramientas vinculadas
model_with_tools = llm_service.llm.bind_tools(tools)  # type: ignore


# 4. Nodos
def agent_node(state: AgentState):
    return {"messages": [model_with_tools.invoke(state["messages"])]}


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
