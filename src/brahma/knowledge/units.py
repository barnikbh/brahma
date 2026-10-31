"""Exact unit conversion with Decimal factors (security-design.md NFR2.2, rules.md BR2.1).

Each table maps a unit to its factor relative to the table's base unit. Converting from
``a`` to ``b`` multiplies by ``factor[a] / factor[b]``. A unit that is not in the table
for the measure (or in a general family such as mass) never converts: the caller gets
``None`` and reports the value as ``unknown_unit``. There is no rounding or tolerance.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

_D = Decimal


def normalise_unit(unit: str) -> str:
    """Lowercase, drop spaces, and spell micro as ``u`` (``µg/g`` and ``mcg/g`` become ``ug/g``)."""
    text = unicodedata.normalize("NFKC", unit).strip().lower()
    text = text.replace("µ", "u").replace("μ", "u").replace("mcg", "ug")
    return re.sub(r"\s+", "", text)


def normalise_measure(measure: str) -> str:
    """Lowercase, trim and collapse spaces, then resolve a known measure synonym."""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", measure).strip().lower())
    return MEASURE_SYNONYMS.get(text, text)


def _table(entries: dict[str, str]) -> dict[str, Decimal]:
    return {normalise_unit(unit): _D(factor) for unit, factor in entries.items()}


MEASURE_SYNONYMS: dict[str, str] = {
    "haemoglobin": "hb",
    "hemoglobin": "hb",
    "faecal calprotectin": "calprotectin",
    "fecal calprotectin": "calprotectin",
    "c-reactive protein": "crp",
}

# Per-measure tables. The first unit listed is the base unit of that table.
UNIT_TABLE: dict[str, dict[str, Decimal]] = {
    "hb": _table({"g/dL": "1", "g/L": "0.1", "mg/dL": "0.001"}),
    "calprotectin": _table({"ug/g": "1", "mg/kg": "1"}),
    "crp": _table({"mg/L": "1", "mg/dL": "10"}),
    "stool frequency": _table({"per day": "1", "/day": "1", "per 24 hours": "1"}),
    "infliximab trough level": _table({"ug/mL": "1", "mg/L": "1"}),
    "stone size": _table({"mm": "1", "cm": "10"}),
    "colonic diameter": _table({"cm": "1", "mm": "0.1"}),
}

# General families used when the measure has no table of its own (doses, durations).
FAMILY_TABLES: dict[str, dict[str, Decimal]] = {
    "mass": _table({"mg": "1", "g": "1000", "ug": "0.001", "kg": "1000000"}),
    "mass_per_kg": _table({"mg/kg": "1", "ug/kg": "0.001", "g/kg": "1000"}),
    "time": _table(
        {
            "hour": "1",
            "hours": "1",
            "day": "24",
            "days": "24",
            "week": "168",
            "weeks": "168",
        }
    ),
}


def to_decimal(value: object) -> Decimal | None:
    """Parse an int, float or numeric string exactly (floats via their shortest repr)."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        if isinstance(value, int):
            number = _D(value)
        elif isinstance(value, float):
            number = _D(repr(value))
        elif isinstance(value, str):
            number = _D(value.strip())
        else:
            return None
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _factors(from_unit: str, to_unit: str, measure: str | None) -> tuple[Decimal, Decimal] | None:
    own = UNIT_TABLE.get(normalise_measure(measure)) if measure is not None else None
    # A measure with its own table converts only within that table.
    tables = [own] if own is not None else list(FAMILY_TABLES.values())
    for table in tables:
        if from_unit in table and to_unit in table:
            return table[from_unit], table[to_unit]
    return None


def convert(
    value: Decimal, from_unit: str | None, to_unit: str | None, measure: str | None = None
) -> Decimal | None:
    """Convert ``value`` exactly, or return None when either unit is unknown for the measure."""
    if from_unit is None or to_unit is None:
        return value if from_unit is None and to_unit is None else None
    source, target = normalise_unit(from_unit), normalise_unit(to_unit)
    if source == target:
        return value
    factors = _factors(source, target, measure)
    if factors is None:
        return None
    return value * factors[0] / factors[1]


def compare(left: Decimal, comparator: str, right: Decimal) -> bool:
    """Apply ``lt``, ``le``, ``gt``, ``ge`` or ``eq`` to two exact numbers."""
    if comparator == "lt":
        return left < right
    if comparator == "le":
        return left <= right
    if comparator == "gt":
        return left > right
    if comparator == "ge":
        return left >= right
    if comparator == "eq":
        return left == right
    raise ValueError(f"unknown comparator: {comparator}")
