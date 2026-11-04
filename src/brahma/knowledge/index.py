"""In-memory read index for one pack version (logical-components.md GraphIndex, NFR1.1).

A ``GraphIndex`` is built once when a version is loaded or created and is never changed:
versions are immutable, so the cache keyed by version needs no invalidation. Every read
on the walk path (search, neighbours, reference ranges, subgraph) uses dict lookups,
with no SQL.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from brahma.knowledge.errors import NodeNotFound
from brahma.knowledge.matcher import (
    drug_class,
    drug_names,
    natural_key,
    node_names,
    normalise_text,
)
from brahma.knowledge.models import (
    Edge,
    EdgeCondition,
    Fact,
    Node,
    PackVersionRef,
    RangeResult,
    ReferenceRange,
    SearchResult,
    Source,
    Step,
    Subgraph,
)
from brahma.knowledge.units import compare, convert, to_decimal

ConditionOutcome = Literal["met", "not_met", "missing"]
SEX_NOT_RECORDED = "sex_not_recorded"


def _age_in_band(age: float, band: str) -> bool:
    if band.endswith("+"):
        return age >= int(band[:-1])
    low, high = (int(part) for part in band.split("-"))
    return low <= age <= high


def _width_key(rng: ReferenceRange) -> tuple[int, Decimal]:
    """Wider ranges sort higher: an open end counts as widest (BR2.4)."""
    low, high = to_decimal(rng.low), to_decimal(rng.high)
    open_ends = (low is None) + (high is None)
    return open_ends, (high or Decimal(0)) - (low or Decimal(0))


class GraphIndex:
    """Read-only lookups for one version: nodes, adjacency, names and sources."""

    def __init__(
        self, version: PackVersionRef, nodes: list[Node], edges: list[Edge], sources: list[Source]
    ) -> None:
        self.version = version
        self.nodes: dict[str, Node] = {
            n.node_id: n.model_copy(update={"pack_version": version}) for n in nodes
        }
        self.out_edges: dict[str, list[Edge]] = {}
        self.in_edges: dict[str, list[Edge]] = {}
        for edge in sorted(edges, key=lambda e: natural_key(e.edge_id)):
            self.out_edges.setdefault(edge.from_node_id, []).append(edge)
            self.in_edges.setdefault(edge.to_node_id, []).append(edge)
        self.names: dict[str, list[str]] = {}
        self.by_source: dict[str, list[str]] = {}
        for node in sorted(self.nodes.values(), key=lambda n: natural_key(n.node_id)):
            for name in node_names(node):
                self.names.setdefault(name, []).append(node.node_id)
            for source_id in node.source_ids:
                self.by_source.setdefault(source_id, []).append(node.node_id)
        # Therapy names: a drug's generic name or synonym -> itself, its generic name and
        # its class; a class -> itself. A therapy fact matches a condition through these.
        self.therapy_names: dict[str, set[str]] = {}
        for node in self.nodes.values():
            klass = drug_class(node)
            names = drug_names(node)
            for name in names:
                known = self.therapy_names.setdefault(name, {name})
                known.update(names[:1])
                if klass:
                    known.add(klass)
            if klass:
                self.therapy_names.setdefault(klass, {klass})
        self.sources: list[Source] = sorted(
            (s for s in sources if s.source_id in self.by_source),
            key=lambda s: natural_key(s.source_id),
        )

    # --- lookups -----------------------------------------------------------------------

    def node(self, node_id: str) -> Node:
        """Return a node, or raise NodeNotFound."""
        try:
            return self.nodes[node_id]
        except KeyError:
            raise NodeNotFound(node_id) from None

    def resolve(self, name: str) -> list[Node]:
        """Symptom, metric and test nodes whose name or synonym equals ``name`` (BR2.1)."""
        return [self.nodes[i] for i in self.names.get(normalise_text(name), [])]

    def nodes_citing(self, source_id: str) -> list[Node]:
        return [self.nodes[i] for i in self.by_source.get(source_id, [])]

    # --- search (BR2.1) --------------------------------------------------------------

    def search(self, facts: list[Fact]) -> SearchResult:
        """Entry nodes matching the facts; facts with an unconvertible unit go to unknownUnit."""
        matches: dict[str, Node] = {}
        unknown: list[Fact] = []
        for fact in facts:
            for node in self.resolve(fact.name):
                outcome = self._fact_matches_entry(fact, node)
                if outcome == "met":
                    matches[node.node_id] = node
                elif outcome == "unknown_unit" and fact not in unknown:
                    unknown.append(fact)
        ordered = sorted(matches.values(), key=lambda n: natural_key(n.node_id))
        return SearchResult(matches=ordered, unknown_unit=unknown)

    def _fact_matches_entry(self, fact: Fact, node: Node) -> str:
        fields = node.fields
        if node.type == "symptom":
            minimum = fields.get("durationMin")
            if not minimum:
                return "met"
            return self._numeric_outcome(
                fact, minimum["unit"], "ge", minimum["value"], measure=None
            )
        if node.type == "metric":
            if fields.get("threshold") is None:
                return "met"
            return self._numeric_outcome(
                fact,
                fields["unit"],
                fields.get("comparator") or "eq",
                fields["threshold"],
                measure=fields.get("measure"),
            )
        return "not_met"

    @staticmethod
    def _numeric_outcome(
        fact: Fact, unit: str, comparator: str, threshold: object, measure: str | None
    ) -> str:
        value, limit = to_decimal(fact.value), to_decimal(threshold)
        if value is None or limit is None:
            return "not_met"
        converted = convert(value, fact.unit, unit, measure)
        if converted is None:
            return "unknown_unit"
        return "met" if compare(converted, comparator, limit) else "not_met"

    # --- neighbours (BR2.2, BR2.3) ---------------------------------------------------

    def incoming(self, node_id: str, relation: str | None = None) -> list[Edge]:
        """Every edge into a node, in edge order, optionally filtered by relation."""
        self.node(node_id)
        return [
            e for e in self.in_edges.get(node_id, []) if relation is None or e.relation == relation
        ]

    def outgoing(self, node_id: str, relation: str | None = None) -> list[Edge]:
        """Every outgoing edge, in edge order, optionally filtered by relation."""
        self.node(node_id)
        return [
            e for e in self.out_edges.get(node_id, []) if relation is None or e.relation == relation
        ]

    def neighbours(
        self, node_id: str, facts: list[Fact], relation: str | None = None
    ) -> list[Step]:
        """Every outgoing edge as a Step with status followable, not_taken, alternative or
        unknown_input."""
        self.node(node_id)
        steps: list[Step] = []
        for edge in self.out_edges.get(node_id, []):
            if relation is not None and edge.relation != relation:
                continue
            target = self.nodes[edge.to_node_id]
            steps.append(Step(edge=edge, node=target, status=self._status(edge, target, facts)))
        return steps

    def _status(
        self, edge: Edge, target: Node, facts: list[Fact]
    ) -> Literal["followable", "not_taken", "alternative", "unknown_input"]:
        if edge.relation == "alternative_to" or target.alternative:
            return "alternative"
        if edge.condition is None:
            return "followable"
        outcome = self.evaluate_condition(edge.condition, facts)
        if outcome == "met":
            return "followable"
        return "unknown_input" if outcome == "missing" else "not_taken"

    def evaluate_condition(self, condition: EdgeCondition, facts: list[Fact]) -> ConditionOutcome:
        """``met`` if any matching fact satisfies the condition, ``missing`` if no fact can
        be evaluated (absent, no value, or unknown unit), else ``not_met``.

        A ``therapy`` condition is never ``missing``: no treatment history means the
        history-conditioned edge is simply not taken, so a walk never asks for it."""
        if condition.therapy is not None:
            return self._therapy_outcome(condition, facts)
        targets = {n.node_id for n in self.resolve(condition.name)}
        wanted = normalise_text(condition.name)
        relevant = [
            f
            for f in facts
            if normalise_text(f.name) == wanted
            or targets & {n.node_id for n in self.resolve(f.name)}
        ]
        results = [self._fact_meets(f, condition, targets) for f in relevant]
        if any(r is True for r in results):
            return "met"
        if all(r is None for r in results):
            return "missing"
        return "not_met"

    def _therapy_outcome(self, condition: EdgeCondition, facts: list[Fact]) -> ConditionOutcome:
        wanted = normalise_text(str(condition.therapy))
        response = normalise_text(str(condition.value))
        for fact in facts:
            if fact.kind != "therapy" or fact.value is None:
                continue
            names = self.therapy_names.get(normalise_text(fact.name), set())
            if wanted in names and normalise_text(str(fact.value)) == response:
                return "met"
        return "not_met"

    def _fact_meets(self, fact: Fact, condition: EdgeCondition, targets: set[str]) -> bool | None:
        if fact.value is None:
            return None
        limit = to_decimal(condition.value)
        if limit is None:
            return normalise_text(str(fact.value)) == normalise_text(str(condition.value))
        value = to_decimal(fact.value)
        if value is None:
            return False
        measure = next(
            (
                self.nodes[t].fields.get("measure")
                for t in sorted(targets)
                if self.nodes[t].type == "metric"
            ),
            condition.name,
        )
        converted = convert(value, fact.unit, condition.unit, measure)
        if converted is None:
            return None
        return compare(converted, condition.comparator, limit)

    # --- reference ranges (BR2.4) ----------------------------------------------------

    def reference_range(
        self, node_id: str, sex: str | None, age: float | None, pregnancy: bool | None
    ) -> RangeResult | None:
        """The most specific range for the patient, or the widest one flagged
        ``sex_not_recorded`` when sex is unknown; None when no range applies."""
        ranges = self.node(node_id).reference_ranges or []
        others = [r for r in ranges if self._matches_age_and_pregnancy(r, age, pregnancy)]
        if sex not in ("female", "male"):
            if not others:
                return None
            return RangeResult(range=max(others, key=_width_key), flags=[SEX_NOT_RECORDED])
        candidates = [r for r in others if r.sex in (sex, "any")]
        if not candidates:
            return None
        return RangeResult(range=max(candidates, key=self._specificity), flags=[])

    @staticmethod
    def _matches_age_and_pregnancy(
        rng: ReferenceRange, age: float | None, pregnancy: bool | None
    ) -> bool:
        if rng.age_band is not None and (age is None or not _age_in_band(age, rng.age_band)):
            return False
        return rng.pregnancy is None or rng.pregnancy == pregnancy

    @staticmethod
    def _specificity(rng: ReferenceRange) -> tuple[int, bool, bool, bool]:
        sex_set = rng.sex != "any"
        pregnancy_set = rng.pregnancy is not None
        age_set = rng.age_band is not None
        return sex_set + pregnancy_set + age_set, sex_set, pregnancy_set, age_set

    # --- subgraph (BR2.6) ------------------------------------------------------------

    def subgraph(self, node_ids: list[str]) -> Subgraph:
        """The requested nodes (with column and alternative flag), the edges among them, and
        the IDs not found."""
        wanted = list(dict.fromkeys(node_ids))
        found = [self.nodes[i] for i in wanted if i in self.nodes]
        missing = [i for i in wanted if i not in self.nodes]
        present = {n.node_id for n in found}
        edges = [
            e
            for source in present
            for e in self.out_edges.get(source, [])
            if e.to_node_id in present
        ]
        edges.sort(key=lambda e: natural_key(e.edge_id))
        return Subgraph(nodes=found, edges=edges, missing=missing)
