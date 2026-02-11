from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.graph.prompt import SPECIALIST_PROMPT
from app.graph.state import AgentState
from app.services.llm_service import llm_service


async def specialist_node(state: AgentState):
    """
    Nodo final que genera la respuesta al usuario.
    """
    # 1. Construimos el prompt con todo el historial
    prompt = ChatPromptTemplate.from_messages(  # type: ignore
        [
            ("system", SPECIALIST_PROMPT),
            MessagesPlaceholder(variable_name="messages"),
            ("system", "Genera la respuesta final basada en lo anterior."),
        ]
    )

    # Cadena
    chain = prompt | llm_service.llm  # type: ignore

    # Invocacion al llm
    response = await chain.ainvoke(state)  # type: ignore

    # Retorno del mensaje final
    return {"messages": [response]}
