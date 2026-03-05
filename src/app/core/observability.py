import logging
from collections import Counter
from threading import Lock
from typing import Any

SAFETY_GATE_TRIGGERED_TOTAL = "safety_gate_triggered_total"
SAFETY_GATE_BYPASSED_TOTAL = "safety_gate_bypassed_total"
SAFETY_GATE_ESCALATION_TOTAL = "safety_gate_escalation_total"

logger = logging.getLogger(__name__)
_COUNTERS = Counter[str]()
_COUNTER_LOCK = Lock()


def increment_counter(name: str, value: int = 1) -> int:
    if value < 0:
        msg = "Counter increments must be zero or greater"
        raise ValueError(msg)

    with _COUNTER_LOCK:
        _COUNTERS[name] += value
        return _COUNTERS[name]


def get_counter_value(name: str) -> int:
    with _COUNTER_LOCK:
        return _COUNTERS[name]


def get_counters_snapshot() -> dict[str, int]:
    with _COUNTER_LOCK:
        return dict(_COUNTERS)


def reset_counters() -> None:
    with _COUNTER_LOCK:
        _COUNTERS.clear()


def increment_safety_gate_triggered() -> int:
    return increment_counter(SAFETY_GATE_TRIGGERED_TOTAL)


def increment_safety_gate_bypassed() -> int:
    return increment_counter(SAFETY_GATE_BYPASSED_TOTAL)


def increment_safety_gate_escalation() -> int:
    return increment_counter(SAFETY_GATE_ESCALATION_TOTAL)


def log_safety_event(
    *,
    path: str,
    reason_codes: list[str],
    interaction_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "safety_gate_decision",
        "path": path,
        "reason_codes": reason_codes,
    }
    if interaction_id:
        payload["interaction_id"] = interaction_id
    if details:
        payload["details"] = details

    logger.info("safety_gate_event", extra={"safety": payload})
