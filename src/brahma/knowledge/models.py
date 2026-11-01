"""Pydantic models for the knowledge graph (entities.md, contract C1).

Python attributes are snake_case; the wire and pack-file names are camelCase aliases
(``nodeId``, ``sourceIds``), which are the contract. Every model forbids unknown keys.
"""

from __future__ import annotations

import re
from decimal import Decimal
from itertools import pairwise
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

VERSION_PATTERN = r"^\d+\.\d+$"
PACK_CODE_PATTERN = r"^[A-Z]{2,5}$"

NodeType = Literal[
    "symptom",
    "metric",
    "diagnosis",
    "subtype",
    "test",
    "treatment_tier",
    "drug",
    "monitoring",
    "response_criterion",
    "diet",
    "watch_out",
    "escalation",
    "interaction",
    "allergy_cross_reactivity",
]
Column = Literal["findings", "diagnosis", "tests", "subtype", "treatment", "monitor"]
Relation = Literal[
    "suggests",
    "confirmed_by",
    "refines_to",
    "first_line",
    "escalate_to",
    "offers_drug",
    "monitor_with",
    "diet",
    "watch_for",
    "surgery_if",
    "alternative_to",
    "responds_if",
]
Comparator = Literal["lt", "le", "gt", "ge", "eq"]
VersionStatus = Literal["live", "superseded"]
StepStatus = Literal["followable", "not_taken", "alternative", "unknown_input"]
ClaimKind = Literal[
    "diagnosis", "test", "drug", "dose", "frequency", "duration", "threshold", "tier"
]
Number = int | float
# How a past therapy went, as a treatment-history fact and a ``therapy`` edge condition.
TherapyResponse = Literal["failed", "lost_response", "intolerant", "responded"]
THERAPY_RESPONSES: tuple[str, ...] = ("failed", "lost_response", "intolerant", "responded")


class KgModel(BaseModel):
    """Base model: camelCase aliases, snake_case attributes, unknown keys refused, immutable."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        frozen=True,
    )


# --- Stored entities -------------------------------------------------------------------


class PackVersionRef(KgModel):
    """Names one version of one pack, e.g. ``{pack: "IBD", number: "1.0"}``."""

    pack: str = Field(pattern=PACK_CODE_PATTERN)
    number: str = Field(pattern=VERSION_PATTERN)


class Pack(KgModel):
    """A named body of clinical knowledge for one specialty."""

    pack_id: str
    name: str = Field(min_length=1, max_length=40)
    code: str = Field(pattern=PACK_CODE_PATTERN)
    specialty: str = Field(min_length=1)
    live_version_number: str | None = None


class PackVersion(KgModel):
    """An immutable snapshot of a pack's nodes and edges."""

    pack_version_id: str
    pack: str
    number: str = Field(pattern=VERSION_PATTERN)
    status: VersionStatus
    published_at: str
    published_by: str
    change_summary: str
    based_on: str | None = None


class Source(KgModel):
    """A cited guideline or paper. Its ID carries the pack prefix (e.g. ``IBD-S3``)."""

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    year: int = Field(ge=1990, le=2026)
    section: str = Field(min_length=1)
    url: str | None = None


class PlausibleRange(KgModel):
    """Metric only: the range of values that are physically plausible."""

    low: Number
    high: Number
    unit: str


class ReferenceRange(KgModel):
    """Metric only: a normal range, optionally for a sex, age band and pregnancy status.

    ``age_band`` is written ``"18-64"`` or ``"65+"``.
    """

    sex: Literal["female", "male", "any"] = "any"
    age_band: str | None = Field(default=None, pattern=r"^\d+(-\d+|\+)$")
    pregnancy: bool | None = None
    low: Number | None = None
    high: Number | None = None
    unit: str


class Node(KgModel):
    """One clinical fact or decision point within a version."""

    node_id: str = Field(min_length=1)
    pack_version: PackVersionRef | None = None
    type: NodeType
    label: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1)
    fields: dict[str, Any]
    source_ids: list[str] = Field(min_length=1)
    plausible_range: PlausibleRange | None = None
    reference_ranges: list[ReferenceRange] | None = None
    column: Column
    alternative: bool = False


class EdgeCondition(KgModel):
    """A condition on an edge; exactly one of ``finding``, ``test`` or ``therapy`` names
    the fact. A ``therapy`` condition names a drug or a drug class and, with ``eq``, how a
    past course of it went (one of ``THERAPY_RESPONSES``)."""

    finding: str | None = None
    test: str | None = None
    therapy: str | None = None
    comparator: Comparator
    value: str | Number
    unit: str | None = None

    @model_validator(mode="after")
    def _one_name(self) -> EdgeCondition:
        named = [n for n in (self.finding, self.test, self.therapy) if n is not None]
        if len(named) != 1:
            raise ValueError("a condition names exactly one of finding, test or therapy")
        return self

    @property
    def name(self) -> str:
        """The finding, test or therapy name the condition refers to."""
        for name in (self.finding, self.test, self.therapy):
            if name is not None:
                return name
        return ""  # unreachable: the validator requires one name


class Edge(KgModel):
    """A directed relation between two nodes of the same version."""

    edge_id: str = Field(min_length=1)
    from_node_id: str
    to_node_id: str
    relation: Relation
    condition: EdgeCondition | None = None


class NodeComment(KgModel):
    """A doctor's comment on a node, stored by its pack-prefixed nodeId."""

    comment_id: str
    node_id: str
    author_profile_id: str
    text: str
    created_at: str


# --- Per-type field schemas (BR1.4) ----------------------------------------------------


class Duration(KgModel):
    """A value with a time unit, e.g. ``{value: 6, unit: weeks}``."""

    value: Number
    unit: str


class SymptomFields(KgModel):
    name: str = Field(min_length=1)
    synonyms: list[str]
    duration_min: Duration | None = None


class MetricFields(KgModel):
    measure: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    threshold: Number | None = None
    comparator: Comparator | None = None
    synonyms: list[str] = Field(default_factory=list)


class DiagnosisFields(KgModel):
    name: str = Field(min_length=1)
    code: str | None = None


class SubtypeFields(KgModel):
    name: str = Field(min_length=1)
    extent: str | None = None
    severity: str | None = None
    code: str | None = None


class TestFields(KgModel):
    name: str = Field(min_length=1)
    result_options: list[str] = Field(min_length=1)
    synonyms: list[str] = Field(default_factory=list)


class TreatmentTierFields(KgModel):
    tier: Literal[1, 2, 3]
    entry_criteria: str = Field(min_length=1)
    drug_node_ids: list[str]


class DoseBand(KgModel):
    """One fixed dose for a weight range: above ``weight_min_kg``, up to and including
    ``weight_max_kg``. A missing end means no limit on that side."""

    weight_min_kg: Number | None = None
    weight_max_kg: Number | None = None
    dose_value: Number
    dose_unit: str = Field(min_length=1)


class DrugFields(KgModel):
    drug: str = Field(min_length=1)
    synonyms: list[str]
    drug_class: str = Field(min_length=1)
    route: str = Field(min_length=1)
    dose_value: Number
    dose_unit: str = Field(min_length=1)
    dose_basis: Literal["absolute", "per_kg", "weight_band"]
    rounding: str = Field(min_length=1)
    frequency: str = Field(min_length=1)
    duration: str = Field(min_length=1)
    contraindications: list[str]
    dose_bands: list[DoseBand] | None = None

    @model_validator(mode="after")
    def _bands_cover_every_weight(self) -> DrugFields:
        """A weight-band dose lists ascending bands with no gap, so every weight has a dose."""
        if self.dose_basis != "weight_band":
            return self
        bands = self.dose_bands or []
        if not bands:
            raise ValueError("a weight_band dose needs doseBands")
        if bands[0].weight_min_kg is not None or bands[-1].weight_max_kg is not None:
            raise ValueError("doseBands must cover every weight")
        for lower, upper in pairwise(bands):
            if lower.weight_max_kg is None or lower.weight_max_kg != upper.weight_min_kg:
                raise ValueError("doseBands must be ascending with no gap")
        if all(band.dose_value != self.dose_value for band in bands):
            raise ValueError("doseValue must be one of the doseBands")
        return self

    def band_for(self, weight_kg: Decimal) -> DoseBand:
        """The band holding this weight; the validator guarantees there is one."""
        for band in self.dose_bands or []:
            top = band.weight_max_kg
            if top is None or weight_kg <= Decimal(str(top)):
                return band
        raise ValueError("no dose band for this weight")


class MonitoringFields(KgModel):
    measure: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    threshold: Number
    comparator: Comparator
    interval: str = Field(min_length=1)


class ResponseCriterionFields(KgModel):
    tier: Literal[1, 2, 3]
    measure: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    threshold: Number
    comparator: Comparator
    verdict: Literal["responding", "partial", "not_responding"]


class DietFields(KgModel):
    advice: str = Field(min_length=1)


class WatchOutFields(KgModel):
    sign: str = Field(min_length=1)
    action: str = Field(min_length=1)


class EscalationFields(KgModel):
    trigger: str = Field(min_length=1)
    action: str = Field(min_length=1)


class InteractionFields(KgModel):
    a: str = Field(min_length=1)
    b: str = Field(min_length=1)
    severity: Literal["major", "moderate", "minor"]


class AllergyCrossReactivityFields(KgModel):
    allergen_class: str = Field(min_length=1)
    conflicting_drug_classes: list[str] = Field(min_length=1)


FIELD_SCHEMAS: dict[str, type[KgModel]] = {
    "symptom": SymptomFields,
    "metric": MetricFields,
    "diagnosis": DiagnosisFields,
    "subtype": SubtypeFields,
    "test": TestFields,
    "treatment_tier": TreatmentTierFields,
    "drug": DrugFields,
    "monitoring": MonitoringFields,
    "response_criterion": ResponseCriterionFields,
    "diet": DietFields,
    "watch_out": WatchOutFields,
    "escalation": EscalationFields,
    "interaction": InteractionFields,
    "allergy_cross_reactivity": AllergyCrossReactivityFields,
}


# --- Call shapes (not stored) ----------------------------------------------------------


class Fact(KgModel):
    """A finding, test result or past therapy passed in by a caller (not stored by U1).

    A ``therapy`` fact names a drug (generic) or drug class; its value is a
    ``TherapyResponse``."""

    kind: Literal["finding", "test", "therapy"]
    name: str = Field(min_length=1)
    value: str | Number | None = None
    unit: str | None = None


class Step(KgModel):
    """One outgoing edge from ``neighbours`` with whether it can be followed."""

    edge: Edge
    node: Node
    status: StepStatus


class ChangeSet(KgModel):
    """The input to ``create_version``."""

    add_nodes: list[Node] = Field(default_factory=list)
    update_nodes: list[Node] = Field(default_factory=list)
    remove_node_ids: list[str] = Field(default_factory=list)
    add_edges: list[Edge] = Field(default_factory=list)
    remove_edge_ids: list[str] = Field(default_factory=list)
    add_sources: list[Source] = Field(default_factory=list)
    change_summary: str = Field(min_length=1)

    @field_validator("change_summary")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("changeSummary must not be blank")
        return value


class Claim(KgModel):
    """One checkable claim from a model-written line (shape shared with C6)."""

    kind: ClaimKind
    value: str = Field(min_length=1)
    unit: str | None = None


class ClaimFailure(KgModel):
    """A claim that did not match, with the reason."""

    claim: Claim
    reason: str


class MatchResult(KgModel):
    """The result of ``match_claims``."""

    matched: list[Claim]
    failures: list[ClaimFailure]


class SearchResult(KgModel):
    """The result of ``search``: matched entry nodes and facts whose unit is unknown."""

    matches: list[Node]
    unknown_unit: list[Fact]


class RangeResult(KgModel):
    """The reference range chosen for a patient, with flags such as ``sex_not_recorded``."""

    range: ReferenceRange
    flags: list[str]


class Subgraph(KgModel):
    """Map data: nodes, the edges among them, and requested IDs that were not found."""

    nodes: list[Node]
    edges: list[Edge]
    missing: list[str]


# --- Pack file -------------------------------------------------------------------------


class PackHeader(KgModel):
    code: str = Field(pattern=PACK_CODE_PATTERN)
    name: str = Field(min_length=1, max_length=40)
    specialty: str = Field(min_length=1)


class PackFile(KgModel):
    """The parsed content of one pack YAML file."""

    pack: PackHeader
    version: str = Field(pattern=VERSION_PATTERN)
    change_summary: str | None = None
    sources: list[Source] = Field(min_length=1)
    nodes: list[Node] = Field(min_length=1)
    edges: list[Edge] = Field(default_factory=list)


def parse_version(number: str) -> tuple[int, int]:
    """Split ``"1.10"`` into ``(1, 10)`` so versions compare numerically."""
    if not re.fullmatch(VERSION_PATTERN, number):
        raise ValueError(f"version must be major.minor: {number!r}")
    major, minor = number.split(".")
    return int(major), int(minor)
