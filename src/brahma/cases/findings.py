"""Finding validation (rules.md BR2, FR4.11) over one version's metric nodes.

A metric finding is resolved to its metric node by name or synonym, converted exactly
into the node's unit with U1's unit table, and marked ``ok``, ``invalid``,
``confirm_range`` or ``conflict``. A finding with no metric node is ``ok``; U4 grounds it.
A metric value without a unit is ``invalid``: the unit is never guessed.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from brahma.cases.catalog import NodeCatalog
from brahma.cases.models import Finding, FindingIn, ValidationState
from brahma.knowledge.models import MetricFields, Node, PlausibleRange
from brahma.knowledge.units import convert, to_decimal

BLOCKING_STATES: frozenset[ValidationState] = frozenset({"invalid", "conflict"})


def format_decimal(value: Decimal) -> str:
    """Plain text for an exact number, without exponent or trailing zeros (``290``)."""
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "") else text


def entered_text(value: float | str | None, unit: str | None) -> str | None:
    """The value as the doctor entered it, e.g. ``102 g/L``."""
    if value is None:
        return None
    number = to_decimal(value) if not isinstance(value, str) else None
    text = format_decimal(number) if number is not None else str(value).strip()
    return f"{text} {unit.strip()}" if unit and unit.strip() else text


def _out_of_range(value: Decimal, unit: str, measure: str, rng: PlausibleRange) -> bool:
    in_range_unit = convert(value, unit, rng.unit, measure)
    low, high = to_decimal(rng.low), to_decimal(rng.high)
    if in_range_unit is None or low is None or high is None:
        return True
    return not low <= in_range_unit <= high


def _validate_metric(item: FindingIn, node: Node) -> tuple[ValidationState, Decimal | None, str]:
    """State, converted value (when valid) and the node's unit for one metric finding."""
    fields = MetricFields.model_validate(node.fields)
    number = to_decimal(item.value)
    if number is None or item.unit is None or not item.unit.strip():
        return "invalid", None, fields.unit
    converted = convert(number, item.unit, fields.unit, fields.measure)
    if converted is None:
        return "invalid", None, fields.unit
    if node.plausible_range is not None and _out_of_range(
        converted, fields.unit, fields.measure, node.plausible_range
    ):
        return "confirm_range", converted, fields.unit
    return "ok", converted, fields.unit


def _one(case_id: str, finding_id: str, item: FindingIn, catalog: NodeCatalog) -> Finding:
    node = catalog.metric(item.name)
    state: ValidationState = "ok"
    value: float | str | None = item.value
    unit = item.unit
    if node is not None:
        state, converted, node_unit = _validate_metric(item, node)
        if converted is not None:
            value, unit = float(converted), node_unit
    return Finding(
        finding_id=finding_id,
        case_id=case_id,
        kind=item.kind,
        name=item.name,
        value=value,
        unit=unit,
        entered_value=entered_text(item.value, item.unit),
        duration=item.duration,
        validation_state=state,
        node_id=node.node_id if node is not None else None,
    )


def _mark_conflicts(findings: list[Finding]) -> list[Finding]:
    """Two or more findings on one metric node with different values are all ``conflict``."""
    values: dict[str, set[float | str | None]] = {}
    for f in findings:
        if f.node_id is not None and f.validation_state != "invalid":
            values.setdefault(f.node_id, set()).add(f.value)
    clashing = {node_id for node_id, seen in values.items() if len(seen) > 1}
    return [
        f.model_copy(update={"validation_state": "conflict"})
        if f.node_id in clashing and f.validation_state != "invalid"
        else f
        for f in findings
    ]


def validate_findings(
    case_id: str,
    items: list[FindingIn],
    catalog: NodeCatalog,
    new_finding_id: Callable[[], str],
) -> list[Finding]:
    """Validate every finding of a case against the version's metric nodes (BR2.1-BR2.5)."""
    validated = [_one(case_id, new_finding_id(), item, catalog) for item in items]
    return _mark_conflicts(validated)


def findings_ready(findings: list[Finding]) -> bool:
    """True when no finding is ``invalid`` or ``conflict``, so a walk may start (BR2.7)."""
    return not any(f.validation_state in BLOCKING_STATES for f in findings)
