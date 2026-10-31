"""Load and version checks (rules.md BR1.1, BR1.2, BR1.4, BR3.5; security-design.md NFR6.1).

``PackValidator.validate`` raises ``PackLoadError`` naming the first offending node,
edge or source. It runs before anything is written, on every load and every
``create_version``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from pydantic import ValidationError

from brahma.knowledge.errors import PackLoadError
from brahma.knowledge.matcher import drug_class, drug_names, node_names, normalise_text
from brahma.knowledge.models import (
    FIELD_SCHEMAS,
    THERAPY_RESPONSES,
    Edge,
    EdgeCondition,
    Node,
    Source,
)
from brahma.knowledge.units import convert, to_decimal

PLACEHOLDER = re.compile(r"\[[^\[\]]*\]")
DATE_LIKE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LONG_DIGITS = re.compile(r"\d{8,}")

# Allow-list: a date-like run inside a clinical schedule or dose, e.g. "weeks 0-2-6",
# "taper 40-30-20 mg", is not a patient date.
_SCHEDULE_BEFORE = re.compile(r"(weeks?|days?|months?|doses?|taper\w*)\s*$", re.I)
_UNIT_AFTER = re.compile(r"^\s*(mg|g|ug|µg|mcg|ml|units?|weeks?|days?|months?|hours?|%)\b", re.I)


def iter_strings(value: Any) -> Iterator[str]:
    """Yield every string inside nested dicts and lists."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)


def _is_schedule(text: str, start: int, end: int) -> bool:
    return bool(_SCHEDULE_BEFORE.search(text[:start]) or _UNIT_AFTER.match(text[end:]))


def find_patient_data(text: str) -> str | None:
    """Return a description of the first date, email address or long digit run, if any."""
    for match in DATE_LIKE.finditer(text):
        if not _is_schedule(text, match.start(), match.end()):
            return f"looks like a date: {match.group()}"
    if ISO_DATE.search(text):
        return "looks like an ISO date"
    if EMAIL.search(text):
        return "looks like an email address"
    if LONG_DIGITS.search(text):
        return "contains a run of 8 or more digits"
    return None


class PackValidator:
    """Validates one version's sources, nodes and edges for the pack ``code``."""

    def validate(
        self, code: str, sources: list[Source], nodes: list[Node], edges: list[Edge]
    ) -> None:
        """Raise PackLoadError for the first problem; return None when the version is valid."""
        source_ids = self._check_sources(code, sources)
        by_id: dict[str, Node] = {}
        for node in nodes:
            self._check_node(code, node, source_ids, by_id)
            by_id[node.node_id] = node
        self._check_tier_drugs(by_id)
        self._check_edges(code, edges, by_id)

    # --- sources and nodes -------------------------------------------------------------

    @staticmethod
    def _check_sources(code: str, sources: list[Source]) -> set[str]:
        seen: set[str] = set()
        for source in sources:
            if not source.source_id.startswith(f"{code}-"):
                raise PackLoadError(source.source_id, f"source ID must start with {code}-")
            if source.source_id in seen:
                raise PackLoadError(source.source_id, "duplicate source ID")
            seen.add(source.source_id)
        return seen

    def _check_node(
        self, code: str, node: Node, source_ids: set[str], seen: dict[str, Node]
    ) -> None:
        node_id = node.node_id
        if not node_id.startswith(f"{code}-"):
            raise PackLoadError(node_id, f"node ID must start with the pack code {code}-")
        if node_id in seen:
            raise PackLoadError(node_id, "duplicate node ID")
        if not node.source_ids:
            raise PackLoadError(node_id, "node has no source")
        for source_id in node.source_ids:
            if source_id not in source_ids:
                raise PackLoadError(node_id, f"cites unknown source {source_id}")
        self._check_fields(node)
        if node.type != "metric" and (node.plausible_range or node.reference_ranges):
            raise PackLoadError(node_id, "only metric nodes carry ranges")
        self._check_text(node)

    @staticmethod
    def _check_fields(node: Node) -> None:
        try:
            FIELD_SCHEMAS[node.type].model_validate(node.fields)
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(part) for part in first["loc"])
            reason = "missing field" if first["type"] == "missing" else first["msg"]
            raise PackLoadError(node.node_id, f"{reason} {where}".strip()) from exc

    @staticmethod
    def _check_text(node: Node) -> None:
        texts = [("label", node.label), ("content", node.content)]
        texts.extend(("fields", text) for text in iter_strings(node.fields))
        for where, text in texts:
            placeholder = PLACEHOLDER.search(text)
            if placeholder:
                raise PackLoadError(node.node_id, f"placeholder {placeholder.group()} in {where}")
            problem = find_patient_data(text)
            if problem:
                raise PackLoadError(node.node_id, f"possible patient data in {where}: {problem}")

    @staticmethod
    def _check_tier_drugs(by_id: dict[str, Node]) -> None:
        for node in by_id.values():
            if node.type != "treatment_tier":
                continue
            for drug_id in node.fields.get("drugNodeIds", []):
                target = by_id.get(drug_id)
                if target is None or target.type != "drug":
                    raise PackLoadError(node.node_id, f"drugNodeIds names {drug_id}, not a drug")

    # --- edges -----------------------------------------------------------------------

    def _check_edges(self, code: str, edges: list[Edge], by_id: dict[str, Node]) -> None:
        names: dict[str, list[Node]] = {}
        therapies: set[str] = set()
        for node in by_id.values():
            for name in node_names(node):
                names.setdefault(name, []).append(node)
            therapies.update(drug_names(node))
            klass = drug_class(node)
            if klass:
                therapies.add(klass)
        seen: set[str] = set()
        for edge in edges:
            if edge.edge_id in seen:
                raise PackLoadError(edge.edge_id, "duplicate edge ID")
            seen.add(edge.edge_id)
            if not edge.edge_id.startswith(f"{code}-"):
                raise PackLoadError(edge.edge_id, f"edge ID must start with {code}-")
            for end in (edge.from_node_id, edge.to_node_id):
                if end not in by_id:
                    raise PackLoadError(edge.edge_id, f"edge end {end} is not in this version")
            if edge.from_node_id == edge.to_node_id:
                raise PackLoadError(edge.edge_id, "self-edge")
            if edge.condition is not None and edge.condition.therapy is not None:
                self._check_therapy(edge.edge_id, edge.condition, therapies)
            elif edge.condition is not None:
                self._check_condition(edge.edge_id, edge.condition, names)

    @staticmethod
    def _check_therapy(edge_id: str, condition: EdgeCondition, therapies: set[str]) -> None:
        """A therapy condition names a drug or drug class of this version, with ``eq`` and
        a known response."""
        if normalise_text(str(condition.therapy)) not in therapies:
            raise PackLoadError(edge_id, f"condition names unknown therapy {condition.therapy}")
        if condition.comparator != "eq":
            raise PackLoadError(edge_id, "a therapy condition must use eq")
        if str(condition.value) not in THERAPY_RESPONSES:
            raise PackLoadError(edge_id, f"{condition.value} is not a therapy response")

    @staticmethod
    def _check_condition(
        edge_id: str, condition: EdgeCondition, names: dict[str, list[Node]]
    ) -> None:
        targets = names.get(normalise_text(condition.name))
        if not targets:
            raise PackLoadError(edge_id, f"condition names unknown finding/test {condition.name}")
        number = to_decimal(condition.value)
        if number is None:
            if condition.comparator != "eq":
                raise PackLoadError(edge_id, "a text condition must use eq")
            for target in targets:
                options = target.fields.get("resultOptions")
                if options and normalise_text(str(condition.value)) not in {
                    normalise_text(o) for o in options
                }:
                    raise PackLoadError(edge_id, f"{condition.value} is not a result option")
            return
        for target in targets:
            unit = target.fields.get("unit")
            measure = target.fields.get("measure")
            if (
                target.type == "metric"
                and condition.unit
                and unit
                and convert(number, condition.unit, unit, measure) is None
            ):
                raise PackLoadError(edge_id, f"condition unit {condition.unit} is unknown")
