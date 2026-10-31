"""Validate structured model output against a request's JSON schema with Pydantic (BR3.4).

The contract passes ``responseSchema`` as a JSON-schema dict, so it is turned into a
Pydantic model. The supported subset is what Pydantic's own ``model_json_schema`` emits
for plain models: object, array, string, integer, number, boolean, null, enum, anyOf,
``$ref`` into ``$defs``, ``required`` and ``additionalProperties: false``. Unknown
keywords are ignored. Validation is strict (no "5" for 5).
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, create_model

_SCALARS: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "null": type(None),
}


def _resolve(node: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    ref = node.get("$ref")
    if isinstance(ref, str):
        resolved: dict[str, Any] = defs[ref.rsplit("/", 1)[-1]]
        return resolved
    return node


def _union(types: list[Any]) -> Any:
    return types[0] if len(types) == 1 else Union[tuple(types)]  # noqa: UP007


def _type_for(node: dict[str, Any], defs: dict[str, Any], name: str) -> Any:
    node = _resolve(node, defs)
    if "enum" in node:
        literal: Any = Literal
        return literal[tuple(node["enum"])]
    if "anyOf" in node:
        return _union([_type_for(n, defs, f"{name}_{i}") for i, n in enumerate(node["anyOf"])])
    kind = node.get("type")
    if isinstance(kind, list):
        return _union([_type_for({**node, "type": k}, defs, name) for k in kind])
    if kind in _SCALARS:
        return _SCALARS[kind]
    if kind == "array":
        return list[_type_for(node.get("items", {}), defs, f"{name}_item")]  # type: ignore[misc]
    if kind == "object" and "properties" in node:
        return _object_model(node, defs, name)
    if kind == "object":
        return dict[str, Any]
    return Any


def _object_model(node: dict[str, Any], defs: dict[str, Any], name: str) -> type[BaseModel]:
    required = set(node.get("required", []))
    fields: dict[str, Any] = {}
    for index, (prop, sub) in enumerate(node.get("properties", {}).items()):
        field_type = _type_for(sub, defs, f"{name}_{index}")
        if prop in required:
            fields[f"f{index}"] = (field_type, Field(alias=prop))
        else:
            fields[f"f{index}"] = (field_type | None, Field(default=None, alias=prop))
    extra: Literal["forbid", "ignore"] = (
        "forbid" if node.get("additionalProperties") is False else "ignore"
    )
    config = ConfigDict(extra=extra, strict=True, serialize_by_alias=True)
    model: type[BaseModel] = create_model(name, __config__=config, **fields)
    return model


@lru_cache(maxsize=64)
def _model_for(schema_json: str) -> type[BaseModel]:
    schema = json.loads(schema_json)
    return _object_model(schema, schema.get("$defs", {}), "StructuredOutput")


def model_for_schema(schema: dict[str, Any]) -> type[BaseModel]:
    """The (cached) Pydantic model for an object JSON schema."""
    return _model_for(json.dumps(schema, sort_keys=True))


def first_json_object(text: str) -> dict[str, Any] | None:
    """The first JSON object in ``text`` (models sometimes wrap JSON in prose), or None."""
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            value, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    return None
