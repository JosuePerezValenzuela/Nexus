import pytest

from app.schemas.safety import SafetyPath, SafetyReasonCode
from app.services import safety_gate_service


def test_detects_urgent_hypoglycemia_and_escalates() -> None:
    decision = safety_gate_service.evaluate_safety(
        user_text=(
            "Tengo diabetes y ahora estoy con sudor frio, confusion y casi me "
            "desmayo"
        ),
        draft_text="Podria ser una baja de azucar.",
    )

    assert decision.path == SafetyPath.ESCALATION
    assert decision.escalated is True
    assert SafetyReasonCode.URGENT_HYPOGLYCEMIA_RED_FLAG in decision.reason_codes
    assert "busca atencion medica inmediata" in decision.final_response.lower()


def test_detects_urgent_hyperglycemia_and_escalates() -> None:
    decision = safety_gate_service.evaluate_safety(
        user_text=(
            "Tengo diabetes, vomitos con aliento afrutado y siento azucar alta "
            "todo el dia"
        ),
        draft_text="Ajusta insulina rapida en casa.",
    )

    assert decision.path == SafetyPath.ESCALATION
    assert decision.escalated is True
    assert SafetyReasonCode.URGENT_HYPERGLYCEMIA_RED_FLAG in decision.reason_codes
    assert SafetyReasonCode.HIGH_RISK_DOSING_DIRECTIVE not in decision.reason_codes


def test_detects_severe_context_combination_as_urgent() -> None:
    decision = safety_gate_service.evaluate_safety(
        user_text=(
            "Tengo diabetes, mareo y vision borrosa con dolor de pecho desde "
            "hace una hora"
        ),
        draft_text="Segui controlandote en casa.",
    )

    assert decision.path == SafetyPath.ESCALATION
    assert decision.escalated is True
    assert SafetyReasonCode.SEVERE_CONTEXT_NEURO_CARDIO in decision.reason_codes


def test_non_urgent_query_passes_through_without_template() -> None:
    draft = (
        "La prediabetes se maneja con dieta, actividad fisica y controles "
        "periodicos."
    )
    decision = safety_gate_service.evaluate_safety(
        user_text="Que es la prediabetes y como se previene?",
        draft_text=draft,
    )

    assert decision.path == SafetyPath.PASS_THROUGH
    assert decision.escalated is False
    assert decision.sanitized is False
    assert decision.final_response == draft


def test_sanitizes_dosing_and_diagnostic_language() -> None:
    draft = (
        "Aumenta 4 unidades de insulina esta noche. "
        "Es diabetes confirmada. "
        "Consulta a tu medico si persisten sintomas."
    )
    decision = safety_gate_service.evaluate_safety(
        user_text="Tengo dudas con mi tratamiento de diabetes.",
        draft_text=draft,
    )

    assert decision.path == SafetyPath.SANITIZED
    assert decision.sanitized is True
    assert SafetyReasonCode.HIGH_RISK_DOSING_DIRECTIVE in decision.reason_codes
    assert SafetyReasonCode.HIGH_RISK_DIAGNOSTIC_DIRECTIVE in decision.reason_codes
    assert "4 unidades" not in decision.final_response
    assert "confirmada" not in decision.final_response


def test_returns_fallback_when_evaluation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(safety_gate_service, "_normalize_text", _boom)

    decision = safety_gate_service.evaluate_safety(
        user_text="Tengo diabetes y sintomas.",
        draft_text="Texto",
    )

    assert decision.path == SafetyPath.FALLBACK
    assert decision.reason_codes == [SafetyReasonCode.SAFETY_GATE_ERROR]
