from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages  # type: ignore


class AgentState(TypedDict):
    # add_messages es el Reducer: concatena en lugar de sobreescribir
    messages: Annotated[list[Any], add_messages]
