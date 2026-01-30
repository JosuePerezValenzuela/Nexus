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
async def supervisor_node(state: AgentState):
    # Uso de with_structured_output para garantizar que devuelva el json correcto
    supervisor_chain = prompt | llm_service.llm.with_structured_output(RouteResponse)  # type: ignore

    result = await supervisor_chain.ainvoke(state)  # type: ignore

    if not result:
        return {"next": "FINISH"}

    decision: RouteResponse = result  # type: ignore

    # Devolvemos la decision en el estado, LangGraph moderno prefiere devolver el
    # comando para el router condicional
    # Solo se devuelve la decision para que el router la lea.
    return {"next": decision.next}
