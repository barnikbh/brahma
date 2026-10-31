"""Shared Pydantic base and helpers for U2 models.

Python attributes are snake_case; the contract names are camelCase aliases (``profileId``).
Every model refuses unknown keys and is immutable once built.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

MAX_PAYLOAD_BYTES = 256 * 1024


class PfModel(BaseModel):
    """Base model: camelCase aliases, snake_case attributes, unknown keys refused, immutable."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        frozen=True,
    )


def to_json(value: Any) -> str:
    """Serialise to compact JSON, keeping non-ASCII characters such as µ as they are."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def json_size(value: Any) -> int:
    """Size in bytes of ``value`` serialised as UTF-8 JSON."""
    return len(to_json(value).encode("utf-8"))


def check_payload_size(value: Any, what: str) -> None:
    """Raise ValueError when ``value`` serialises to more than 256 KB (BR1.2)."""
    if json_size(value) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"{what} is larger than 256 KB")


def new_id(prefix: str) -> str:
    """A new random identifier such as ``ae-3f2c...``."""
    return f"{prefix}-{uuid.uuid4().hex}"


def utc_now() -> str:
    """The current UTC time as ISO 8601 with microseconds, so text order is time order."""
    return datetime.now(UTC).isoformat(timespec="microseconds")
