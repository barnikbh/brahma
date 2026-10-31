"""``ClaimScanner``: claims found in a line's text, whatever the model declared (BR1.1).

The scan is deterministic. It finds:

- every number followed by a dose or measurement unit (``120 mg``, ``5 mg/kg``,
  ``45 mg/L``): a measurement unit (``g/dL``, ``mg/L``, ``per day``, ``mm``) is a
  ``threshold`` claim and every other unit is a ``dose`` claim;
- every drug, test or diagnosis name or synonym known to the pinned version, longest
  name first so ``acute severe ulcerative colitis`` is one claim, not two.

The vocabulary is built once per pack version and cached (NFR1.3). Versions are
immutable, so the cache never needs invalidating.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from brahma.knowledge.matcher import normalise_text
from brahma.knowledge.models import Claim, ClaimKind, Node, PackVersionRef
from brahma.knowledge.repository import version_id
from brahma.knowledge.service import KnowledgeService
from brahma.knowledge.units import normalise_unit, to_decimal

# Display spellings, matched case-insensitively. Longest first so "mg/kg" wins over "mg".
_UNITS = (
    "per day",
    "mcg/kg",
    "µg/kg",
    "ug/kg",
    "mg/kg",
    "g/kg",
    "mcg/mL",
    "µg/mL",
    "ug/mL",
    "mcg/g",
    "µg/g",
    "ug/g",
    "mg/dL",
    "mg/L",
    "g/dL",
    "g/L",
    "/day",
    "mcg",
    "µg",
    "ug",
    "mg",
    "mm",
    "cm",
    "g",
)
# Measurement units: a number in one of these is a threshold. Every other unit (mg, g/kg,
# mg/day, ...) is a dose.
THRESHOLD_UNITS = frozenset(
    normalise_unit(u)
    for u in ("per day", "/day", "g/dL", "g/L", "mg/dL", "mg/L", "ug/g", "ug/mL", "mm", "cm")
)
_NUMBER_WITH_UNIT = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*("
    + "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True))
    # Any other per-something mass unit ("60 mg/day") is still caught, so it cannot hide.
    + r"|(?:mcg|µg|ug|mg|g)/\w+"
    + r")(?![\w/])",
    re.IGNORECASE,
)
_NAME_KINDS: dict[str, ClaimKind] = {
    "drug": "drug",
    "test": "test",
    "diagnosis": "diagnosis",
    "subtype": "diagnosis",
}


def clean_text(text: str) -> str:
    """NFKC, curly apostrophes made straight, lowercased and spaces collapsed."""
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    return normalise_text(text)


def _names(node: Node) -> list[str]:
    fields = node.fields
    if node.type == "drug":
        names = [fields.get("drug"), *fields.get("synonyms", [])]
    elif node.type == "test":
        names = [fields.get("name"), *fields.get("synonyms", [])]
    elif node.type in ("diagnosis", "subtype"):
        names = [fields.get("name")]
    else:
        return []
    return [clean_text(n) for n in names if isinstance(n, str) and n.strip()]


@dataclass(frozen=True)
class Vocabulary:
    """Name lookups for one version: a compiled pattern and each name's claim kind."""

    pattern: re.Pattern[str] | None
    kinds: dict[str, ClaimKind]


def build_vocabulary(nodes: list[Node]) -> Vocabulary:
    """The drug, test and diagnosis names of a version, as one longest-first pattern."""
    kinds: dict[str, ClaimKind] = {}
    for node in nodes:
        kind = _NAME_KINDS.get(node.type)
        if kind is None:
            continue
        for name in _names(node):
            kinds.setdefault(name, kind)
    if not kinds:
        return Vocabulary(None, kinds)
    alternatives = "|".join(re.escape(n) for n in sorted(kinds, key=len, reverse=True))
    return Vocabulary(re.compile(rf"(?<![\w])({alternatives})(?![\w])"), kinds)


def scan_numbers(text: str) -> list[Claim]:
    """Every number with a dose or measurement unit, as ``dose`` or ``threshold`` claims."""
    claims: list[Claim] = []
    for match in _NUMBER_WITH_UNIT.finditer(unicodedata.normalize("NFKC", text)):
        value, unit = match.group(1), match.group(2)
        kind: ClaimKind = "threshold" if normalise_unit(unit) in THRESHOLD_UNITS else "dose"
        claims.append(Claim(kind=kind, value=value, unit=unit))
    return claims


_TIER_VALUE = re.compile(r"(?i)^\s*(?:tier\s*)?(\d+(?:\.\d+)?)\s*$")


def normalize_declared(claim: Claim) -> Claim:
    """Parse a model-declared claim value the way the text scanner would.

    A live model declares the value as it wrote it in the line ("100 mg",
    "Tier 2") instead of the bare number the matcher needs ("100" plus unit
    "mg"). The scanned twin of that claim then matches while the declared one
    fails and rejects an otherwise grounded line. Parsing the declared value
    with the same number rule keeps the exact match (a wrong value still fails);
    a value that does not parse is kept as it is and fails as a model error.
    """
    if claim.kind in ("dose", "threshold"):
        if to_decimal(claim.value) is not None:
            return claim
        found = scan_numbers(claim.value)
        if len(found) == 1:
            return Claim(kind=claim.kind, value=found[0].value, unit=found[0].unit)
        return claim
    if claim.kind == "tier":
        match = _TIER_VALUE.match(claim.value)
        if match is not None:
            return Claim(kind="tier", value=match.group(1))
        return claim
    return claim


class ClaimScanner:
    """Scans line text for claims against the vocabulary of the pinned version."""

    def __init__(self, knowledge: KnowledgeService) -> None:
        self._knowledge = knowledge
        self._vocabularies: dict[str, Vocabulary] = {}

    def vocabulary(self, version: PackVersionRef) -> Vocabulary:
        """The cached vocabulary of a version (built on first use)."""
        key = version_id(version.pack, version.number)
        vocabulary = self._vocabularies.get(key)
        if vocabulary is None:
            vocabulary = build_vocabulary(self._knowledge.repo.read_nodes(key))
            self._vocabularies[key] = vocabulary
        return vocabulary

    def scan(self, text: str, version: PackVersionRef) -> list[Claim]:
        """Number-with-unit claims, then name claims, in the order they appear."""
        claims = scan_numbers(text)
        vocabulary = self.vocabulary(version)
        if vocabulary.pattern is not None:
            for match in vocabulary.pattern.finditer(clean_text(text)):
                name = match.group(1)
                claims.append(Claim(kind=vocabulary.kinds[name], value=name))
        return claims


def merge_claims(*groups: list[Claim]) -> list[Claim]:
    """Declared and scanned claims without duplicates, first occurrence kept."""
    seen: set[tuple[str, str, str]] = set()
    merged: list[Claim] = []
    for group in groups:
        for claim in group:
            key = (claim.kind, clean_text(claim.value), normalise_unit(claim.unit or ""))
            if key not in seen:
                seen.add(key)
                merged.append(claim)
    return merged
