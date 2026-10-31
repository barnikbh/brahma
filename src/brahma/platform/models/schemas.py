"""Model gateway request and response models (contract C4)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from brahma.platform.base import PfModel, check_payload_size

# ``draft_proposal`` is U5's knowledge-update drafting (u5 code-generation plan, Step 9).
# ``write_section`` and ``why`` are U4's grounded walk (u4 code-generation plan, Step 9).
# ``treatment_history`` reads past therapies from a follow-up message (U4 follow-up turn).
Purpose = Literal[
    "extract",
    "narrate",
    "explain",
    "draft",
    "draft_proposal",
    "plain_benchmark",
    "followup",
    "write_section",
    "why",
    "treatment_history",
    "knowledge_update",
]
_ROLES = {"system", "user", "assistant"}


class ModelRequest(PfModel):
    """One completion request. ``messages`` are ``{role, content}`` dicts."""

    purpose: Purpose
    messages: list[dict[str, Any]] = Field(min_length=1)
    max_tokens: int = Field(ge=1, le=32000)
    response_schema: dict[str, Any] | None = None

    @field_validator("messages")
    @classmethod
    def _check_messages(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for message in messages:
            if message.get("role") not in _ROLES or not isinstance(message.get("content"), str):
                raise ValueError("each message needs a role (system|user|assistant) and text")
        check_payload_size(messages, "messages")
        return messages


class ModelResponse(PfModel):
    """The model's reply, plus who answered and how long it took."""

    text: str
    parsed: dict[str, Any] | None = None
    provider: str
    model: str
    latency_ms: int = Field(ge=0)
    input_tokens: int | None = None
    output_tokens: int | None = None


class CurrentModel(PfModel):
    """The active provider and model (C4 ``current()``)."""

    provider: str
    model: str
