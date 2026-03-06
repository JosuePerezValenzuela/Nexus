import importlib
import sys
from types import ModuleType
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


class _StubGraph:
    def __init__(self, response_text: str, safety_meta: dict[str, Any] | None) -> None:
        self._response_text = response_text
        self._safety_meta = safety_meta

    async def ainvoke(self, _: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {"messages": [AIMessage(content=self._response_text)]}
        if self._safety_meta is not None:
            result["safety_meta"] = self._safety_meta
        return result


def _load_agent_module_with_stub_graph(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response_text: str,
    safety_meta: dict[str, Any] | None,
):
    workflow_stub = ModuleType("app.graph.workflow")
    workflow_module = cast(Any, workflow_stub)
    workflow_module.graph = _StubGraph(
        response_text=response_text,
        safety_meta=safety_meta,
    )
    monkeypatch.setitem(sys.modules, "app.graph.workflow", workflow_stub)
    sys.modules.pop("app.api.v1.endpoints.agent", None)
    return importlib.import_module("app.api.v1.endpoints.agent")


def _build_test_client(agent_module: Any) -> TestClient:
    app = FastAPI()
    app.state.limiter = agent_module.limiter
    app.include_router(agent_module.router, prefix="/api/v1/agent")
    return TestClient(app)


# Verifica que un caso urgente en /chat fuerce salida de plantilla de escalamiento.
def test_chat_endpoint_forces_escalation_output_for_urgent_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urgent_text = (
        "Esto puede ser una situacion urgente. No puedo indicar dosis ni confirmar "
        "diagnosticos. Busca atencion medica inmediata ahora."
    )
    agent_module = _load_agent_module_with_stub_graph(
        monkeypatch,
        response_text=urgent_text,
        safety_meta={
            "path": "escalation",
            "reason_codes": ["urgent_hypoglycemia_red_flag"],
            "escalated": True,
            "sanitized": False,
        },
    )
    monkeypatch.setattr(agent_module.settings, "SAFETY_GATE_ENABLED", True)
    monkeypatch.setattr(agent_module.settings, "SAFETY_GATE_EXPOSE_METADATA", True)

    with _build_test_client(agent_module) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"message": "Tengo diabetes y confusion intensa"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert "situacion urgente" in payload["response"].lower()
    assert "atencion medica inmediata" in payload["response"].lower()
    assert payload["safety"]["path"] == "escalation"


# Verifica que la metadata de safety se oculte cuando el toggle esta desactivado.
def test_chat_endpoint_hides_safety_metadata_when_exposure_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_module = _load_agent_module_with_stub_graph(
        monkeypatch,
        response_text="Respuesta segura de ejemplo.",
        safety_meta={
            "path": "pass_through",
            "reason_codes": [],
            "escalated": False,
            "sanitized": False,
        },
    )
    monkeypatch.setattr(agent_module.settings, "SAFETY_GATE_ENABLED", True)
    monkeypatch.setattr(agent_module.settings, "SAFETY_GATE_EXPOSE_METADATA", False)

    with _build_test_client(agent_module) as client:
        response = client.post(
            "/api/v1/agent/chat",
            json={"message": "Que es la prediabetes?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "Respuesta segura de ejemplo."
    assert "safety" not in payload
