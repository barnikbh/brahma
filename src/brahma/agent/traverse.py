"""The deterministic graph walk (BR2.2-BR2.4, BR2.10). The model never picks a node.

1. ``choose_version`` searches every live pack (or the case's pinned version first) and
   keeps the one whose findings reach a diagnosis (BR2.10), so urology needs no code.
2. ``walk_graph`` follows C1 ``neighbours`` from the matched findings: ``suggests`` to a
   diagnosis, ``confirmed_by`` tests, ``refines_to`` sub-types (only edges whose
   conditions the facts meet), then the entry treatment tier (``first_line``), its drugs
   and next tier, ``monitor_with`` / ``responds_if``, ``diet`` and ``watch_for`` /
   ``surgery_if``. The result is the section plan in FR4.6 order.
3. When a refinement edge needs a test result that is missing, the tests are returned as
   ``needed_tests`` (BR2.3); the walk still goes as far as the answered tests allow.
4. When no pack matches the findings the outcome is ``out_of_knowledge`` (BR2.4).
5. Treatment history (``therapy`` facts) opens ``escalate_to`` edges with a ``therapy``
   condition from any walked tier. The tiers they reach become the entry ("start here")
   and their drugs, monitoring and watch-outs form ``history_sections``, the part of the
   plan a follow-up writes. Drugs the history names are marked ``tried`` on the map.
6. Offered drugs render as grey ``option`` nodes and tier-sourced monitoring, watch-outs
   and escalation tiers as grey ``planned`` nodes; the doctor's recorded choice (per
   tier) marks one drug ``chosen`` and lights its tier's downstream ``used``.
7. Review-scoped facts (day-3 results, never presenting findings) move the entry tier
   along followable non-therapy ``escalate_to`` edges. Therapy-conditioned and
   unconditional escalations stay for history and the doctor to decide.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from brahma.agent.models import SECTION_ORDER, MapStatus
from brahma.knowledge.matcher import (
    drug_class,
    drug_names,
    natural_key,
    node_names,
    normalise_text,
)
from brahma.knowledge.models import Fact, Node, PackVersionRef, Step
from brahma.knowledge.repository import version_id
from brahma.knowledge.service import KnowledgeService

TraversalOutcome = Literal["walked", "out_of_knowledge"]
ENTRY_TYPES = frozenset({"symptom", "metric"})
# Map statuses on the traversed path: an edge renders walked only between two of these.
TRAVERSED_STATUSES = frozenset({"used", "entry", "chosen", "tried", "test_needed"})
TREATMENT_RELATIONS = ("offers_drug", "escalate_to")
MONITOR_RELATIONS = ("responds_if", "monitor_with")
WATCH_RELATIONS = ("watch_for", "surgery_if")
HISTORY_SECTIONS = ("treatment", "monitor", "watch_outs")
# A drug the history says did not work, or was not tolerated, is not suggested again.
NOT_AGAIN = frozenset({"failed", "lost_response", "intolerant"})


@dataclass
class Traversal:
    """The walk over one version: the section plan plus what the map needs."""

    version: PackVersionRef | None
    outcome: TraversalOutcome
    sections: dict[str, list[str]] = field(default_factory=dict)
    needed_tests: list[str] = field(default_factory=list)
    entry_tier_ids: list[str] = field(default_factory=list)
    alternative_ids: list[str] = field(default_factory=list)
    test_results: dict[str, str] = field(default_factory=dict)
    walked_edge_ids: list[str] = field(default_factory=list)
    history_tier_ids: list[str] = field(default_factory=list)
    history_sections: dict[str, list[str]] = field(default_factory=dict)
    tried: dict[str, str] = field(default_factory=dict)
    # Drugs the entry tiers offer (the clickable grey options), and the tier-sourced
    # monitoring, watch-outs and escalation tiers (grey until a drug is chosen).
    option_ids: list[str] = field(default_factory=list)
    planned_ids: list[str] = field(default_factory=list)
    # Entry tier -> the planned downstream that lights up when one of its drugs is chosen.
    tier_downstream: dict[str, list[str]] = field(default_factory=dict)
    # Entry tier -> chosen drug. Applied last, so a choice beats option/planned.
    choices: dict[str, str] = field(default_factory=dict)

    def section(self, section_id: str) -> list[str]:
        """The node IDs walked for a section, in walk order (empty when none)."""
        return list(self.sections.get(section_id, []))

    @property
    def path_node_ids(self) -> list[str]:
        """Every walked node, section by section, without duplicates."""
        ordered = [n for s in SECTION_ORDER for n in self.sections.get(s, [])]
        return list(dict.fromkeys(ordered))

    def statuses(self) -> dict[str, MapStatus]:
        """The map status of each walked, needed, offered, planned or alternative node."""
        result: dict[str, MapStatus] = {n: "used" for n in self.path_node_ids}
        for test_id in self.section("tests"):
            if test_id not in self.test_results:
                result[test_id] = "test_needed"
        for node_id in self.option_ids:
            if node_id in result:
                result[node_id] = "option"
        for node_id in self.planned_ids:
            if node_id in result:
                result[node_id] = "planned"
        for tier_id in self.entry_tier_ids:
            result[tier_id] = "entry"
        for drug_id in self.tried:
            result[drug_id] = "tried"
        for tier_id, drug_id in self.choices.items():
            if result.get(drug_id) != "option":
                continue  # stale choice (e.g. the drug is tried): light nothing
            result[drug_id] = "chosen"
            for member in self.tier_downstream.get(tier_id, []):
                if result.get(member) == "planned":
                    result[member] = "used"
        for alt in self.alternative_ids:
            result.setdefault(alt, "not_taken")
        return result


def _add(target: list[str], node_ids: Iterable[str]) -> None:
    for node_id in node_ids:
        if node_id not in target:
            target.append(node_id)


class GraphWalker:
    """Walks one version for one set of facts. Create one per walk."""

    def __init__(self, knowledge: KnowledgeService, version: PackVersionRef, facts: list[Fact]):
        self._knowledge = knowledge
        self._version = version
        self._facts = facts
        self._steps: dict[str, list[Step]] = {}
        self.result = Traversal(version=version, outcome="walked")

    # --- helpers ---------------------------------------------------------------------

    def steps(self, node_id: str) -> list[Step]:
        """Outgoing steps of a node for the walk's facts (cached)."""
        if node_id not in self._steps:
            self._steps[node_id] = self._knowledge.neighbours(self._version, node_id, self._facts)
        return self._steps[node_id]

    def _follow(self, node_id: str, relations: Iterable[str]) -> list[str]:
        wanted = set(relations)
        targets: list[str] = []
        for step in self.steps(node_id):
            if step.edge.relation in wanted and step.status == "followable":
                _add(targets, [step.node.node_id])
                _add(self.result.walked_edge_ids, [step.edge.edge_id])
        return targets

    def _section(self, section_id: str) -> list[str]:
        return self.result.sections.setdefault(section_id, [])

    # --- the walk --------------------------------------------------------------------

    def entries(self) -> list[Node]:
        """Finding nodes (symptom or metric) that the facts match (C1 search)."""
        found = self._knowledge.search(self._version, self._facts).matches
        return [n for n in found if n.type in ENTRY_TYPES]

    def diagnosis(self, entries: list[Node]) -> str | None:
        """The diagnosis most findings suggest; ties go to the lowest node ID."""
        votes: dict[str, int] = {}
        for entry in entries:
            for step in self.steps(entry.node_id):
                if (
                    step.edge.relation == "suggests"
                    and step.status == "followable"
                    and step.node.type == "diagnosis"
                ):
                    votes[step.node.node_id] = votes.get(step.node.node_id, 0) + 1
        if not votes:
            return None
        best = sorted(votes, key=lambda n: (-votes[n], natural_key(n)))[0]
        for entry in entries:
            for step in self.steps(entry.node_id):
                if step.node.node_id == best and step.status == "followable":
                    _add(self.result.walked_edge_ids, [step.edge.edge_id])
        return best

    def run(self) -> Traversal:
        """Walk from the findings to the section plan."""
        entries = self.entries()
        diagnosis = self.diagnosis(entries)
        if diagnosis is None:
            return Traversal(version=self._version, outcome="out_of_knowledge")
        self.result.test_results = self._results()
        _add(self._section("findings"), [e.node_id for e in entries])
        _add(self._section("diagnosis"), [diagnosis])
        leaves = self._refine(diagnosis)
        tiers = self._treatment(leaves)
        self._monitor(tiers)
        self._diet_and_watch(tiers)
        self._tried()
        history = self._history()
        for tier in history:
            self._history_plan(tier)
        if history:
            self.result.history_tier_ids = history
            self.result.entry_tier_ids = list(history)
        self.result.sections = {s: ids for s, ids in self.result.sections.items() if ids}
        return self.result

    def _results(self) -> dict[str, str]:
        """Test node ID -> result, matching each test fact by test name or synonym."""
        results: dict[str, str] = {}
        key = version_id(self._version.pack, self._version.number)
        tests = [n for n in self._knowledge.repo.read_nodes(key) if n.type == "test"]
        for fact in self._facts:
            if fact.kind != "test" or fact.value is None or not str(fact.value).strip():
                continue
            wanted = normalise_text(fact.name)
            for node in tests:
                if wanted in node_names(node):
                    results[node.node_id] = str(fact.value)
        return results

    def _refine(self, diagnosis: str) -> list[str]:
        """Breadth-first over ``refines_to``; returns the deepest nodes reached (leaves)."""
        frontier, seen, leaves = [diagnosis], {diagnosis}, []
        while frontier:
            node_id = frontier.pop(0)
            tests = [
                s.node.node_id for s in self.steps(node_id) if s.edge.relation == "confirmed_by"
            ]
            _add(self._section("tests"), tests)
            _add(self.result.walked_edge_ids, self._edge_ids(node_id, "confirmed_by"))
            _add(
                self.result.alternative_ids,
                [s.node.node_id for s in self.steps(node_id) if s.status == "alternative"],
            )
            refines = [s for s in self.steps(node_id) if s.edge.relation == "refines_to"]
            followable = self._follow(node_id, ["refines_to"])
            if not followable:
                leaves.append(node_id)
                blocked = [s for s in refines if s.status == "unknown_input"]
                if blocked:
                    self._need([*tests, *self._tests_for(blocked)])
            for target in followable:
                if target in seen:
                    continue
                seen.add(target)
                node = self._knowledge.get_node(self._version, target)
                section = "diagnosis" if node.type == "diagnosis" else "subtype"
                _add(self._section(section), [target])
                frontier.append(target)
        return leaves

    def _edge_ids(self, node_id: str, relation: str) -> list[str]:
        return [s.edge.edge_id for s in self.steps(node_id) if s.edge.relation == relation]

    def _need(self, test_ids: Iterable[str]) -> None:
        _add(
            self.result.needed_tests,
            [t for t in test_ids if t not in self.result.test_results],
        )

    def _treatment(self, leaves: list[str]) -> list[str]:
        """Entry tiers from the leaves, then their drugs and next tier (FR4.6)."""
        tiers: list[str] = []
        for leaf in leaves:
            _add(tiers, self._follow(leaf, ["first_line"]))
            blocked = [
                s
                for s in self.steps(leaf)
                if s.edge.relation == "first_line" and s.status == "unknown_input"
            ]
            if blocked and not tiers:
                self._need(self._tests_for(blocked))
        tiers = self._review_escalated(tiers)
        self.result.entry_tier_ids = list(tiers)
        treatment = self._section("treatment")
        for tier in tiers:
            _add(treatment, [tier])
            drugs = self._follow(tier, ["offers_drug"])
            _add(treatment, drugs)
            _add(self.result.option_ids, drugs)
            for step in self.steps(tier):
                if step.edge.relation == "escalate_to" and step.status != "not_taken":
                    _add(treatment, [step.node.node_id])
                    _add(self.result.planned_ids, [step.node.node_id])
        return tiers

    def _tests_for(self, blocked: list[Step]) -> list[str]:
        """The walked tests whose results the blocked edges' conditions need."""
        names = {normalise_text(s.edge.condition.name) for s in blocked if s.edge.condition}
        return [
            t
            for t in self.result.section("tests")
            if names & set(node_names(self._knowledge.get_node(self._version, t)))
        ]

    # --- treatment history ------------------------------------------------------------

    def _tried(self) -> None:
        """Drugs the therapy facts name (generic name, synonym or class), among the walked
        drugs and the drugs the walked tiers offer; offered ones join the path to show."""
        therapies = {
            normalise_text(f.name): str(f.value)
            for f in self._facts
            if f.kind == "therapy" and f.value is not None
        }
        if not therapies:
            return
        treatment = self._section("treatment")
        offered: dict[str, str | None] = {n: None for n in treatment}
        for tier in list(treatment):
            for step in self.steps(tier):
                if step.edge.relation == "offers_drug":
                    offered.setdefault(step.node.node_id, step.edge.edge_id)
        for node_id, edge_id in offered.items():
            node = self._knowledge.get_node(self._version, node_id)
            response = next(
                (therapies[n] for n in [*drug_names(node), drug_class(node)] if n in therapies),
                None,
            )
            if response is None:
                continue
            self.result.tried[node_id] = response
            _add(treatment, [node_id])
            if edge_id is not None:
                _add(self.result.walked_edge_ids, [edge_id])

    def _history(self) -> list[str]:
        """Tiers reached by followable ``escalate_to`` edges with a therapy condition."""
        frontier = [
            n
            for n in self.result.section("treatment")
            if self._knowledge.get_node(self._version, n).type == "treatment_tier"
        ]
        seen, found = set(frontier), list[str]()
        while frontier:
            node_id = frontier.pop(0)
            for step in self.steps(node_id):
                condition = step.edge.condition
                if (
                    step.edge.relation == "escalate_to"
                    and condition is not None
                    and condition.therapy is not None
                    and step.status == "followable"
                ):
                    _add(found, [step.node.node_id])
                    _add(self.result.walked_edge_ids, [step.edge.edge_id])
                    if step.node.node_id not in seen:
                        seen.add(step.node.node_id)
                        frontier.append(step.node.node_id)
        return found

    def _review_escalated(self, tiers: list[str]) -> list[str]:
        """Entry tiers after review evidence: follow followable non-therapy escalations.

        Only review-scoped facts count, so a presenting value never skips a tier.
        """
        review = [f for f in self._facts if f.context == "review"]
        if not review:
            return tiers
        entry: list[str] = []
        for tier in tiers:
            node, seen = tier, {tier}
            while True:
                nxt = [
                    s.node.node_id
                    for s in self._knowledge.neighbours(self._version, node, review, "escalate_to")
                    if s.status == "followable"
                    and s.edge.condition is not None
                    and s.edge.condition.therapy is None
                    and s.node.node_id not in seen
                ]
                if not nxt:
                    break
                node = nxt[0]
                seen.add(node)
            _add(entry, [node])
        return entry

    def _history_plan(self, tier: str) -> None:
        """The tier, its drugs (less those that failed), its monitoring and watch-outs."""
        plan = self.result.history_sections
        drugs = [
            d
            for d in self._follow(tier, ["offers_drug"])
            if self.result.tried.get(d) not in NOT_AGAIN
        ]
        _add(self.result.option_ids, drugs)
        monitor = self._follow(tier, MONITOR_RELATIONS)
        watch = self._follow(tier, WATCH_RELATIONS)
        _add(self.result.planned_ids, [*monitor, *watch])
        _add(self.result.tier_downstream.setdefault(tier, []), [*monitor, *watch])
        parts = {
            "treatment": [tier, *drugs],
            "monitor": monitor,
            "watch_outs": watch,
        }
        for section_id in HISTORY_SECTIONS:
            _add(plan.setdefault(section_id, []), parts[section_id])
            _add(self._section(section_id), parts[section_id])
        self.result.history_sections = {s: ids for s, ids in plan.items() if ids}

    def _monitor(self, tiers: list[str]) -> None:
        for tier in tiers:
            found = self._follow(tier, MONITOR_RELATIONS)
            _add(self._section("monitor"), found)
            _add(self.result.planned_ids, found)
            _add(self.result.tier_downstream.setdefault(tier, []), found)

    def _diet_and_watch(self, tiers: list[str]) -> None:
        path = [*self.result.section("diagnosis"), *self.result.section("subtype")]
        for node_id in path:
            _add(self._section("diet"), self._follow(node_id, ["diet"]))
        tier_set = set(tiers)
        for node_id in [*path, *tiers]:
            found = self._follow(node_id, WATCH_RELATIONS)
            _add(self._section("watch_outs"), found)
            if node_id in tier_set:
                _add(self.result.planned_ids, found)
                _add(self.result.tier_downstream.setdefault(node_id, []), found)


def walk_graph(
    knowledge: KnowledgeService, version: PackVersionRef, facts: list[Fact]
) -> Traversal:
    """The deterministic walk of ``facts`` over ``version`` (BR2.2-BR2.4)."""
    return GraphWalker(knowledge, version, facts).run()


def choose_version(
    knowledge: KnowledgeService, facts: list[Fact], pinned: PackVersionRef | None
) -> PackVersionRef | None:
    """The version to walk: the pinned one when its findings reach a diagnosis, else the
    live pack whose findings reach a diagnosis with the most matched findings (BR2.10).
    None when no pack matches (out of knowledge)."""
    candidates: list[PackVersionRef] = []
    if pinned is not None:
        candidates.append(pinned)
    for live in knowledge.repo.live_versions():
        if pinned is None or live.pack != pinned.pack:
            candidates.append(PackVersionRef(pack=live.pack, number=live.number))
    if pinned is not None and _reaches_diagnosis(knowledge, pinned, facts) is not None:
        return pinned
    scored: list[tuple[int, str, PackVersionRef]] = []
    for version in candidates:
        matched = _reaches_diagnosis(knowledge, version, facts)
        if matched is not None:
            scored.append((-matched, version.pack, version))
    return sorted(scored, key=lambda s: (s[0], s[1]))[0][2] if scored else None


def _reaches_diagnosis(
    knowledge: KnowledgeService, version: PackVersionRef, facts: list[Fact]
) -> int | None:
    walker = GraphWalker(knowledge, version, facts)
    entries = walker.entries()
    return len(entries) if walker.diagnosis(entries) is not None else None


def lane_nodes(
    knowledge: KnowledgeService, version: PackVersionRef, branch_node_id: str
) -> list[str]:
    """An explored branch's nodes: the branch, its tests, tiers, drugs and watch-outs."""
    nodes = [branch_node_id]
    for step in knowledge.neighbours(version, branch_node_id, []):
        if step.edge.relation in ("confirmed_by", "first_line", "watch_for", "surgery_if"):
            _add(nodes, [step.node.node_id])
            if step.edge.relation == "first_line":
                for drug in knowledge.neighbours(version, step.node.node_id, [], "offers_drug"):
                    _add(nodes, [drug.node.node_id])
    return nodes
