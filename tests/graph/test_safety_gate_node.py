import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.core import observability
from app.graph.nodes import safety_gate
from app.graph.state import AgentState
from app.schemas.safety import SafetyPath, SafetyReasonCode


def _build_state(user_text: str, draft_text: str) -> AgentState:
    return {
        "messages": [
            HumanMessage(content=user_text),
            AIMessage(content=draft_text),
        ],
        "next": None,
    }


# Verifica que un caso urgente termine en ruta de escalamiento en el nodo.
def test_safety_gate_node_returns_escalation_for_urgent_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(safety_gate.settings, "SAFETY_GATE_ENABLED", True)
    observability.reset_counters()

    result = asyncio.run(
        safety_gate.safety_gate_node(
            _build_state(
                user_text="Tengo diabetes, sudor frio y confusion intensa.",
                draft_text="Podria ser algo leve, ajusta dosis en casa.",
            )
        )
    )

    messages = result["messages"]
    assert isinstance(messages, list)
    final_message = cast(list[Any], messages)[0]
    final_content = str(final_message.content)
    assert "busca atencion medica inmediata" in final_content.lower()

    safety_meta = result["safety_meta"]
    assert isinstance(safety_meta, dict)
    assert safety_meta["path"] == SafetyPath.ESCALATION.value


# Verifica que un caso no urgente mantenga pass-through sin sobreescribir mensaje.
def test_safety_gate_node_keeps_pass_through_for_non_urgent_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(safety_gate.settings, "SAFETY_GATE_ENABLED", True)
    observability.reset_counters()

    draft_text = "La prediabetes se aborda con habitos y controles periodicos."
    result = asyncio.run(
        safety_gate.safety_gate_node(
            _build_state(
                user_text="Que es la prediabetes?",
                draft_text=draft_text,
            )
        )
    )

    assert "messages" not in result
    safety_meta = result["safety_meta"]
    assert isinstance(safety_meta, dict)
    assert safety_meta["path"] == SafetyPath.PASS_THROUGH.value


# Verifica que ante falla interna se use fallback conservador y reason code de error.
def test_safety_gate_node_uses_fallback_when_service_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(safety_gate.settings, "SAFETY_GATE_ENABLED", True)
    monkeypatch.setattr("app.services.safety_gate_service._normalize_text", _boom)
    observability.reset_counters()

    result = asyncio.run(
        safety_gate.safety_gate_node(
            _build_state(
                user_text="Tengo sintomas preocupantes.",
                draft_text="Respuesta borrador.",
            )
        )
    )

    messages = result["messages"]
    assert isinstance(messages, list)
    final_message = cast(list[Any], messages)[0]
    final_content = str(final_message.content)
    assert "no puedo confirmar diagnosticos" in final_content.lower()

    safety_meta = result["safety_meta"]
    assert isinstance(safety_meta, dict)
    assert safety_meta["path"] == SafetyPath.FALLBACK.value
    assert safety_meta["reason_codes"] == [SafetyReasonCode.SAFETY_GATE_ERROR.value]


# Verifica integridad de contadores por interaccion y escalamiento solo en urgentes.
def test_safety_gate_counters_reconcile_triggered_bypassed_and_escalation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(safety_gate.settings, "SAFETY_GATE_ENABLED", True)
    observability.reset_counters()

    asyncio.run(
        safety_gate.safety_gate_node(
            _build_state(
                user_text="Tengo diabetes, vomitos y aliento afrutado.",
                draft_text="Ajusta insulina en casa.",
            )
        )
    )
    asyncio.run(
        safety_gate.safety_gate_node(
            _build_state(
                user_text="Que es la prediabetes?",
                draft_text="Es una condicion previa que se controla con habitos.",
            )
        )
    )

    triggered = observability.get_counter_value(
        observability.SAFETY_GATE_TRIGGERED_TOTAL
    )
    bypassed = observability.get_counter_value(observability.SAFETY_GATE_BYPASSED_TOTAL)
    escalation = observability.get_counter_value(
        observability.SAFETY_GATE_ESCALATION_TOTAL
    )

    assert triggered == 1
    assert bypassed == 1
    assert escalation == 1
    assert triggered + bypassed == 2


# Verifica que el flujo mantenga specialist -> safety_gate -> END en workflow.
def test_workflow_declares_safety_gate_after_specialist() -> None:
    workflow_file = Path("src/app/graph/workflow.py")
    content = workflow_file.read_text(encoding="utf-8")

    specialist_edge = 'workflow.add_edge("specialist", "safety_gate")'
    end_edge = 'workflow.add_edge("safety_gate", END)'

    assert specialist_edge in content
    assert end_edge in content
    assert content.index(specialist_edge) < content.index(end_edge)
