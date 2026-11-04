"""Exact claim matching (rules.md BR2.5, security-design.md NFR2.2).

Pure functions, no model calls. Text is equal after normalisation and synonym
resolution; numbers are equal as Decimals after exact unit conversion. There is no
rounding, tolerance or fuzzy matching.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

from brahma.knowledge.models import Claim, ClaimFailure, MatchResult, Node
from brahma.knowledge.units import convert, to_decimal

NO_FIELD = "no_field_for_kind"
VALUE_DIFFERS = "value_differs"
UNKNOWN_UNIT = "unknown_unit"
NOT_A_NUMBER = "value_not_a_number"
PER_KG_DOSE = "dose_basis_per_kg"


def normalise_text(text: str) -> str:
    """Lowercase, trim and collapse internal whitespace (NFKC first)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().lower()


def natural_key(item_id: str) -> tuple[str, int, str]:
    """Sort key so ``IBD-N2`` comes before ``IBD-N10``."""
    match = re.fullmatch(r"(.*?)(\d+)(\D*)", item_id)
    if match is None:
        return item_id, -1, ""
    return match.group(1), int(match.group(2)), match.group(3)


def node_names(node: Node) -> list[str]:
    """Names a fact or condition can use for a symptom, metric or test node (BR2.1)."""
    fields = node.fields
    primary: Any
    if node.type == "symptom":
        primary = fields.get("name")
    elif node.type == "metric":
        primary = fields.get("measure")
    elif node.type == "test":
        primary = fields.get("name")
    else:
        return []
    names = [primary, *fields.get("synonyms", [])]
    return [normalise_text(name) for name in names if isinstance(name, str)]


def drug_names(node: Node) -> list[str]:
    """A drug node's generic name and synonyms, normalised (empty for other types)."""
    if node.type != "drug":
        return []
    fields = node.fields
    names = [fields.get("drug"), *fields.get("synonyms", [])]
    return [normalise_text(name) for name in names if isinstance(name, str)]


def drug_class(node: Node) -> str | None:
    """A drug node's class, normalised (None for other types)."""
    value = node.fields.get("drugClass") if node.type == "drug" else None
    return normalise_text(value) if isinstance(value, str) else None


def _text_matches(claim: Claim, values: Iterable[Any]) -> str | None:
    wanted = normalise_text(claim.value)
    known = {normalise_text(v) for v in values if isinstance(v, str)}
    return None if wanted in known else VALUE_DIFFERS


def _number_matches(claim: Claim, value: Any, unit: str | None, measure: str | None) -> str | None:
    claimed = to_decimal(claim.value)
    expected = to_decimal(value)
    if claimed is None or expected is None:
        return NOT_A_NUMBER
    if unit is None and claim.unit is None:
        return None if claimed == expected else VALUE_DIFFERS
    converted = convert(claimed, claim.unit, unit, measure)
    if converted is None:
        return UNKNOWN_UNIT
    return None if converted == expected else VALUE_DIFFERS


def _match_tier(claim: Claim, node: Node) -> str | None:
    claimed: Decimal | None = to_decimal(claim.value)
    if claimed is None:
        return NOT_A_NUMBER
    return None if claimed == to_decimal(node.fields.get("tier")) else VALUE_DIFFERS


def _match_dose(claim: Claim, node: Node) -> str | None:
    fields = node.fields
    induction = fields.get("inductionDoseValue")
    if induction is not None and (
        _number_matches(claim, induction, fields.get("inductionDoseUnit"), None) is None
    ):
        return None  # the stated starting dose, held in its own field
    if fields.get("doseBasis") == "weight_band":
        reasons = [
            _number_matches(claim, band.get("doseValue"), band.get("doseUnit"), None)
            for band in fields.get("doseBands") or []
        ]
        return None if None in reasons else (reasons[0] if reasons else NO_FIELD)
    if fields.get("doseBasis") != "absolute":
        return PER_KG_DOSE
    return _number_matches(claim, fields.get("doseValue"), fields.get("doseUnit"), None)


def _match_threshold(claim: Claim, node: Node) -> str | None:
    fields = node.fields
    if fields.get("threshold") is None:
        return NO_FIELD
    return _number_matches(claim, fields["threshold"], fields.get("unit"), fields.get("measure"))


def _matcher_for(claim: Claim, node: Node) -> Callable[[], str | None] | None:
    fields = node.fields
    kind, node_type = claim.kind, node.type
    if kind == "diagnosis" and node_type in ("diagnosis", "subtype"):
        return lambda: _text_matches(claim, [fields.get("name")])
    if kind == "test" and node_type == "test":
        return lambda: _text_matches(claim, [fields.get("name"), *fields.get("synonyms", [])])
    if kind == "drug" and node_type == "drug":
        return lambda: _text_matches(claim, [fields.get("drug"), *fields.get("synonyms", [])])
    if kind == "dose" and node_type == "drug":
        return lambda: _match_dose(claim, node)
    if kind in ("frequency", "duration") and node_type == "drug":
        return lambda: _text_matches(claim, [fields.get(kind)])
    if kind == "threshold" and node_type in ("metric", "monitoring", "response_criterion"):
        return lambda: _match_threshold(claim, node)
    if kind == "tier" and node_type in ("treatment_tier", "response_criterion"):
        return lambda: _match_tier(claim, node)
    return None


def match_claims(node: Node, claims: Iterable[Claim]) -> MatchResult:
    """Compare each claim with one node's fields.

    A claim passes only when its kind maps to a field of the node's type and the values
    are equal. A dose claim matches only an absolute dose: per-kg doses are computed by
    the caller (U3) and passed as an absolute claim. Failure reasons are
    ``no_field_for_kind``, ``value_differs``, ``unknown_unit``, ``value_not_a_number``
    and ``dose_basis_per_kg``.
    """
    matched: list[Claim] = []
    failures: list[ClaimFailure] = []
    for claim in claims:
        check = _matcher_for(claim, node)
        reason = NO_FIELD if check is None else check()
        if reason is None:
            matched.append(claim)
        else:
            failures.append(ClaimFailure(claim=claim, reason=reason))
    return MatchResult(matched=matched, failures=failures)


def find_supporting_node(nodes: Iterable[Node], claims: list[Claim]) -> Node | None:
    """Return the first node, in natural nodeId order, for which every claim matches.

    With no claims there is nothing to support, so the result is None.
    """
    if not claims:
        return None
    for node in sorted(nodes, key=lambda n: natural_key(n.node_id)):
        if not match_claims(node, claims).failures:
            return node
    return None
