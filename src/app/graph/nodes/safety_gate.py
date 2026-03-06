from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.core.config import settings
from app.core.observability import (
    increment_safety_gate_bypassed,
    increment_safety_gate_escalation,
    increment_safety_gate_triggered,
    log_safety_event,
)
from app.graph.state import AgentState
from app.schemas.safety import SafetyDecision, SafetyPath
from app.services.safety_gate_service import evaluate_safety


def _message_to_text(message: BaseMessage) -> str:
    raw_content = cast(Any, message).content
    if isinstance(raw_content, str):
        return raw_content.strip()

    if not isinstance(raw_content, list):
        return str(raw_content).strip()

    parts: list[str] = []
    for raw_item in cast(list[object], raw_content):
        if isinstance(raw_item, str):
            parts.append(raw_item)
            continue

        if not isinstance(raw_item, dict):
            continue

        mapped_item = cast(dict[str, object], raw_item)
        text = mapped_item.get("text")
        if isinstance(text, str):
            parts.append(text)

    return " ".join(parts).strip()


def _latest_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _message_to_text(message)
    return ""


def _build_safety_meta(decision: SafetyDecision) -> dict[str, Any]:
    return {
        "path": decision.path.value,
        "reason_codes": [code.value for code in decision.reason_codes],
        "escalated": decision.escalated,
        "sanitized": decision.sanitized,
    }


async def safety_gate_node(state: AgentState) -> dict[str, Any]:
    messages = state.get("messages", [])
    if not messages:
        return {}

    draft_message = messages[-1]
    draft_text = _message_to_text(draft_message)

    if not settings.SAFETY_GATE_ENABLED:
        return {}

    user_text = _latest_user_text(messages)
    decision = evaluate_safety(user_text=user_text, draft_text=draft_text)

    if decision.path == SafetyPath.PASS_THROUGH:
        increment_safety_gate_bypassed()
    else:
        increment_safety_gate_triggered()

    if decision.path == SafetyPath.ESCALATION:
        increment_safety_gate_escalation()

    safety_meta = _build_safety_meta(decision)
    log_safety_event(
        path=decision.path.value,
        reason_codes=safety_meta["reason_codes"],
        details={"escalated": decision.escalated, "sanitized": decision.sanitized},
    )

    if decision.path == SafetyPath.PASS_THROUGH:
        return {"safety_meta": safety_meta}

    return {
        "messages": [AIMessage(content=decision.final_response)],
        "safety_meta": safety_meta,
    }
