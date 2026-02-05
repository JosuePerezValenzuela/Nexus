from typing import Literal

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from app.graph.prompt import SUPERVISOR_PROMPT
from app.graph.state import AgentState
from app.services.llm_service import llm_service

# Definimos las opciones de ruteo (El "menu" del supervisor)
# FINISH: Cuando ya tiene la respuesta final para el usuario

options = ["DOCS_AGENT", "DATA_AGENT", "FINISH"]


# Schema de Salida (Obligamos al LLM a elegir una de las opciones)
class RouteResponse(BaseModel):
    next: Literal["DOCS_AGENT", "DATA_AGENT", "FINISH"] = Field(
        description="El sigueinte nodo/agente al se debe llamar"
    )


# Prompt del supervisor
SYSTEM_PROMPT = SUPERVISOR_PROMPT

prompt = ChatPromptTemplate.from_messages(  # type: ignore
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Dada la conversacion anterior, ¿quien deberia actuar ahora? "
            "O deberiamos terminar (FINISH)? Selecciona uno: {options}",
        ),
    ]
).partial(options=str(options))


# El nodo supervisor
async def supervisor_node(state: AgentState):  # type: ignore
    supervisor_chain = prompt | llm_service.llm.with_structured_output(  # type: ignore
        RouteResponse, method="json_mode"
    )

    try:
        result = await supervisor_chain.ainvoke(state)  # type: ignore

        # Si el parsing falla, terminamos
        if not result or not result.next:  # type: ignore
            return {"next": "FINISH"}

        return {"next": result.next}  # type: ignore

    except Exception as e:
        # Si el llm alucina, terminamos para evitar bucles
        print(f"Error en supervisor: {e}")
        return {"next": "FINISH"}
