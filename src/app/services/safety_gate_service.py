import re
import unicodedata

from app.core.config import settings
from app.schemas.safety import SafetyDecision, SafetyPath, SafetyReasonCode

ESCALATION_TEMPLATE = (
    "Esto puede ser una situacion urgente. "
    "No puedo indicar dosis ni confirmar diagnosticos.\n\n"
    "1) Busca atencion medica inmediata o comunicate con emergencias locales ahora.\n"
    "2) Si podes, no te quedes solo/a y comparti tus sintomas actuales.\n"
    "3) Lleva lista de medicamentos y valores recientes de glucosa.\n\n"
    "Motivos detectados: {reason_codes_humanized}"
)

FALLBACK_TEMPLATE = (
    "No puedo confirmar diagnosticos ni indicar dosis de medicacion en este momento. "
    "Si tenes sintomas preocupantes, busca atencion medica inmediata o comunica"
    "te con emergencias locales."
)

HYPOGLYCEMIA_RED_FLAGS = (
    "hipoglucemia",
    "hipoglicemia",
    "glucosa baja",
    "azucar baja",
    "desmayo",
    "inconsciente",
    "convulsion",
    "convulsiones",
    "sudor frio",
)

HYPERGLYCEMIA_RED_FLAGS = (
    "hiperglucemia",
    "glucosa alta",
    "azucar alta",
    "cetoacidosis",
    "aliento afrutado",
    "vomitos",
    "respiracion rapida",
    "deshidratacion intensa",
)

SEVERE_CONTEXT_MARKERS = (
    "dolor de pecho",
    "falta de aire",
    "dificultad para respirar",
    "no puede respirar",
    "debilidad de un lado",
    "habla arrastrada",
    "confusion intensa",
    "perdida de conocimiento",
)

ELEVATED_RISK_SYMPTOMS = (
    "mareo",
    "nausea",
    "nauseas",
    "palpitaciones",
    "dolor de cabeza",
    "vision borrosa",
    "debilidad",
)

DIABETES_CONTEXT_MARKERS = (
    "diabetes",
    "prediabetes",
    "glucosa",
    "azucar",
    "insulina",
)

DOSING_PATTERNS = (
    re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:u|ui|unidades?|mg|mcg|ml)\b"),
    re.compile(
        r"\b(?:aumenta|aumente|subi|sube|ajusta|ajuste|inyectate|"
        r"inyecte|toma|tom[aá])\b.{0,30}\b(?:insulina|metformina|medicacion)\b"
    ),
)

DIAGNOSTIC_PATTERNS = (
    re.compile(r"\b(?:diagnostico|diagnosticado|confirmado|confirma)\b"),
    re.compile(
        r"\b(?:es|tenes|tienes|presentas)\s+"
        r"(?:diabetes|cetoacidosis|hipoglucemia|hiperglucemia)\b"
    ),
)

REASON_HUMANIZATION: dict[SafetyReasonCode, str] = {
    SafetyReasonCode.URGENT_HYPOGLYCEMIA_RED_FLAG: (
        "senales compatibles con hipoglucemia severa"
    ),
    SafetyReasonCode.URGENT_HYPERGLYCEMIA_RED_FLAG: (
        "senales compatibles con hiperglucemia severa"
    ),
    SafetyReasonCode.SEVERE_CONTEXT_NEURO_CARDIO: (
        "combinacion de sintomas y contexto neuro-cardiovascular de riesgo"
    ),
    SafetyReasonCode.HIGH_RISK_DOSING_DIRECTIVE: (
        "instrucciones de dosis/titulacion no seguras"
    ),
    SafetyReasonCode.HIGH_RISK_DIAGNOSTIC_DIRECTIVE: (
        "lenguaje de diagnostico definitivo no permitido"
    ),
    SafetyReasonCode.SAFETY_GATE_ERROR: "error de evaluacion del safety gate",
}


def evaluate_safety(user_text: str, draft_text: str) -> SafetyDecision:
    try:
        urgent_codes = _detect_urgent_reason_codes(user_text)
        if urgent_codes:
            return _build_escalation_decision(urgent_codes)

        prohibited_codes = _detect_prohibited_directives(draft_text)
        if prohibited_codes:
            return _build_sanitized_decision(draft_text, prohibited_codes)

        return SafetyDecision(
            path=SafetyPath.PASS_THROUGH,
            reason_codes=[],
            final_response=draft_text.strip(),
            escalated=False,
            sanitized=False,
        )
    except Exception:
        return _build_fallback_decision()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    without_diacritics = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    compact = re.sub(r"\s+", " ", without_diacritics)
    return compact.strip()


def _has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _detect_urgent_reason_codes(user_text: str) -> list[SafetyReasonCode]:
    normalized = _normalize_text(user_text)
    reason_codes: list[SafetyReasonCode] = []

    if _has_any_term(normalized, HYPOGLYCEMIA_RED_FLAGS):
        reason_codes.append(SafetyReasonCode.URGENT_HYPOGLYCEMIA_RED_FLAG)

    if _has_any_term(normalized, HYPERGLYCEMIA_RED_FLAGS):
        reason_codes.append(SafetyReasonCode.URGENT_HYPERGLYCEMIA_RED_FLAG)

    has_diabetes_context = _has_any_term(normalized, DIABETES_CONTEXT_MARKERS)
    has_elevated_symptom = _has_any_term(normalized, ELEVATED_RISK_SYMPTOMS)
    has_severe_marker = _has_any_term(normalized, SEVERE_CONTEXT_MARKERS)

    if has_diabetes_context and has_elevated_symptom and has_severe_marker:
        reason_codes.append(SafetyReasonCode.SEVERE_CONTEXT_NEURO_CARDIO)

    return _limit_reason_codes(reason_codes)


def _detect_prohibited_directives(text: str) -> list[SafetyReasonCode]:
    normalized = _normalize_text(text)
    reason_codes: list[SafetyReasonCode] = []

    if any(pattern.search(normalized) for pattern in DOSING_PATTERNS):
        reason_codes.append(SafetyReasonCode.HIGH_RISK_DOSING_DIRECTIVE)

    if any(pattern.search(normalized) for pattern in DIAGNOSTIC_PATTERNS):
        reason_codes.append(SafetyReasonCode.HIGH_RISK_DIAGNOSTIC_DIRECTIVE)

    return _limit_reason_codes(reason_codes)


def _build_escalation_decision(reason_codes: list[SafetyReasonCode]) -> SafetyDecision:
    reason_text = _humanize_reason_codes(reason_codes)
    final_response = ESCALATION_TEMPLATE.format(reason_codes_humanized=reason_text)
    return SafetyDecision(
        path=SafetyPath.ESCALATION,
        reason_codes=reason_codes,
        final_response=final_response,
        escalated=True,
        sanitized=False,
    )


def _build_sanitized_decision(
    draft_text: str, reason_codes: list[SafetyReasonCode]
) -> SafetyDecision:
    final_response = _sanitize_directives(draft_text)
    return SafetyDecision(
        path=SafetyPath.SANITIZED,
        reason_codes=reason_codes,
        final_response=final_response,
        escalated=False,
        sanitized=True,
    )


def _sanitize_directives(draft_text: str) -> str:
    normalized = _normalize_text(draft_text)
    sentences = re.split(r"(?<=[.!?])\s+", normalized)

    safe_sentences: list[str] = []
    for sentence in sentences:
        if not sentence:
            continue
        if any(pattern.search(sentence) for pattern in DOSING_PATTERNS):
            continue
        if any(pattern.search(sentence) for pattern in DIAGNOSTIC_PATTERNS):
            continue
        safe_sentences.append(sentence)

    if not safe_sentences:
        return (
            "No puedo indicar dosis ni confirmar diagnosticos. "
            "Para una recomendacion segura, consulta a tu equipo tratante."
        )

    safe_body = " ".join(safe_sentences).strip()
    return f"No puedo indicar dosis exactas ni confirmar diagnosticos. {safe_body}"


def _build_fallback_decision() -> SafetyDecision:
    return SafetyDecision(
        path=SafetyPath.FALLBACK,
        reason_codes=[SafetyReasonCode.SAFETY_GATE_ERROR],
        final_response=FALLBACK_TEMPLATE,
        escalated=False,
        sanitized=True,
    )


def _humanize_reason_codes(reason_codes: list[SafetyReasonCode]) -> str:
    labels = [
        REASON_HUMANIZATION.get(code, code.value.replace("_", " "))
        for code in reason_codes
    ]
    return ", ".join(labels)


def _limit_reason_codes(reason_codes: list[SafetyReasonCode]) -> list[SafetyReasonCode]:
    max_codes = max(1, settings.SAFETY_GATE_MAX_REASON_CODES)
    return reason_codes[:max_codes]
