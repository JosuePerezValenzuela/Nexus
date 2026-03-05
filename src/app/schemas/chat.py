from pydantic import BaseModel, Field

from app.schemas.safety import SafetyPath, SafetyReasonCode


def _default_reason_codes() -> list[SafetyReasonCode]:
    return []


class ChatRequest(BaseModel):
    message: str


class ChatSafetyMeta(BaseModel):
    path: SafetyPath
    reason_codes: list[SafetyReasonCode] = Field(default_factory=_default_reason_codes)
    escalated: bool = False
    sanitized: bool = False


class ChatResponse(BaseModel):
    response: str
    safety: ChatSafetyMeta | None = None
