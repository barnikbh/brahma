"""Safe pack-file reading (security-design.md NFR8.1).

A pack file must be ``.yaml`` or ``.yml`` and at most 5 MB. It is parsed with
``NoAliasSafeLoader``: a ``yaml.SafeLoader`` (so ``!!python/...`` tags are refused) that
also refuses anchors' aliases, so a small file cannot expand into a huge document.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from brahma.knowledge.errors import PackLoadError
from brahma.knowledge.models import PackFile

MAX_PACK_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIXES = (".yaml", ".yml")
_ID_KEYS = {"nodes": "nodeId", "edges": "edgeId", "sources": "sourceId"}


class AliasNotAllowed(yaml.YAMLError):
    """Raised when a pack file uses a YAML alias (``*name``)."""


class NoAliasSafeLoader(yaml.SafeLoader):
    """SafeLoader that refuses YAML aliases."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.AliasEvent):
            raise AliasNotAllowed("YAML aliases are not allowed in pack files")
        return super().compose_node(parent, index)


def _locate(data: dict[str, Any], error: ValidationError) -> tuple[str, str]:
    """Name the node, edge or source a validation error belongs to, and the reason."""
    first = error.errors()[0]
    loc = first["loc"]
    item_id = "pack"
    rest: tuple[Any, ...] = loc
    if len(loc) >= 2 and loc[0] in _ID_KEYS and isinstance(loc[1], int):
        items = data.get(str(loc[0]))
        if isinstance(items, list) and loc[1] < len(items) and isinstance(items[loc[1]], dict):
            item_id = str(items[loc[1]].get(_ID_KEYS[str(loc[0])], f"{loc[0]}[{loc[1]}]"))
        rest = loc[2:]
    where = ".".join(str(part) for part in rest)
    return item_id, f"{where}: {first['msg']}" if where else str(first["msg"])


class PackLoader:
    """Reads one pack file into a validated ``PackFile`` model (no database access)."""

    def read(self, path: str | Path) -> PackFile:
        """Check, parse and model-validate a pack file; raise PackLoadError on any problem."""
        file_path = Path(path)
        label = str(file_path)
        if file_path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise PackLoadError(label, "pack files must have a .yaml or .yml extension")
        try:
            size = file_path.stat().st_size
            if size > MAX_PACK_BYTES:
                raise PackLoadError(label, f"pack file is {size} bytes; the limit is 5 MB")
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise PackLoadError(label, f"cannot read pack file: {exc}") from exc
        return self.parse(text, label)

    def parse(self, text: str, label: str = "pack") -> PackFile:
        """Parse YAML text with the safe loader and validate it as a pack."""
        try:
            data = yaml.load(text, Loader=NoAliasSafeLoader)  # a SafeLoader subclass
        except yaml.YAMLError as exc:
            raise PackLoadError(label, f"invalid or unsafe YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise PackLoadError(label, "a pack file must be a YAML mapping")
        try:
            return PackFile.model_validate(data)
        except ValidationError as exc:
            item_id, reason = _locate(data, exc)
            raise PackLoadError(item_id, reason) from exc
