from langgraph.graph import START, StateGraph  # type: ignore
from langgraph.prebuilt import ToolNode, tools_condition

from app.graph.nodes.agent import TOOLS, agent_node
from app.graph.state import AgentState

# Inicializacion del grafo
workflow = StateGraph(AgentState)

# Agregamos los nodos
workflow.add_node("agent", agent_node)  # type: ignore
workflow.add_node("tools", ToolNode(TOOLS))  # type: ignore # Usamos las tools definidas en el nodo

# Definimos las aristas
workflow.add_edge(START, "agent")

# Router Nativo:
# LangGrapg decide
workflow.add_conditional_edges("agent", tools_condition)

# Ciclo de retorno
workflow.add_edge("tools", "agent")

# Compilacion
rag_graph = workflow.compile()  # type: ignore
