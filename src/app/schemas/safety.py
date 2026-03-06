from enum import StrEnum

from pydantic import BaseModel, Field


class SafetyPath(StrEnum):
    PASS_THROUGH = "pass_through"
    ESCALATION = "escalation"
    SANITIZED = "sanitized"
    FALLBACK = "fallback"


class SafetyReasonCode(StrEnum):
    URGENT_HYPOGLYCEMIA_RED_FLAG = "urgent_hypoglycemia_red_flag"
    URGENT_HYPERGLYCEMIA_RED_FLAG = "urgent_hyperglycemia_red_flag"
    SEVERE_CONTEXT_NEURO_CARDIO = "severe_context_neuro_cardio"
    HIGH_RISK_DOSING_DIRECTIVE = "high_risk_dosing_directive"
    HIGH_RISK_DIAGNOSTIC_DIRECTIVE = "high_risk_diagnostic_directive"
    SAFETY_GATE_ERROR = "safety_gate_error"


def _default_reason_codes() -> list[SafetyReasonCode]:
    return []


class SafetyDecision(BaseModel):
    path: SafetyPath
    reason_codes: list[SafetyReasonCode] = Field(default_factory=_default_reason_codes)
    final_response: str
    escalated: bool = False
    sanitized: bool = False
