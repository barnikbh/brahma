"""Pure helpers for the walk engine: facts, form fields, map data and model payloads.

Nothing here calls the model or writes to the database.
"""

from __future__ import annotations

from typing import Any

from brahma.agent.models import (
    SECTION_ORDER,
    SECTION_TITLES,
    FormField,
    MapData,
    MapEdge,
    MapLane,
    MapNode,
    MapStatus,
    SectionState,
    TherapyItem,
    Walk,
)
from brahma.agent.traverse import TRAVERSED_STATUSES, Traversal
from brahma.cases.models import DoseResult, Finding, Patient
from brahma.knowledge.errors import NodeNotFound
from brahma.knowledge.matcher import drug_class, drug_names, normalise_text
from brahma.knowledge.models import Fact, Node, PackVersionRef, Source
from brahma.knowledge.repository import version_id
from brahma.knowledge.service import KnowledgeService

USABLE_STATES = frozenset({"ok", "confirm_range"})
# Everyday words for a drug class, mapped to the class name the packs use.
CLASS_WORDS: dict[str, str] = {
    "steroid": "corticosteroid",
    "steroids": "corticosteroid",
    "corticosteroids": "corticosteroid",
    "anti-tnf": "anti-tnf monoclonal antibody",
    "anti tnf": "anti-tnf monoclonal antibody",
    "anti-tnfs": "anti-tnf monoclonal antibody",
    "anti-tnf agent": "anti-tnf monoclonal antibody",
}
RESPONSE_WORDS: dict[str, str] = {
    "failed": "no response",
    "lost_response": "lost response",
    "intolerant": "not tolerated",
    "responded": "responded",
}


def finding_facts(findings: list[dict[str, Any]]) -> list[Fact]:
    """Facts from the confirmed findings (invalid or conflicting ones are left out)."""
    facts: list[Fact] = []
    for finding in findings:
        name = str(finding.get("name") or "").strip()
        if not name or finding.get("validationState") not in USABLE_STATES:
            continue
        value = finding.get("value")
        if not isinstance(value, (int, float, str)) or isinstance(value, bool):
            value = None
        facts.append(Fact(kind="finding", name=name, value=value, unit=finding.get("unit")))
    return facts


def answer_facts(
    knowledge: KnowledgeService, version: PackVersionRef, answers: dict[str, str]
) -> list[Fact]:
    """Test-result facts. A key is a test node ID or, for ``run_walk``, a test name."""
    facts: list[Fact] = []
    for key, value in answers.items():
        if not key.strip() or not value.strip():
            continue
        try:
            node = knowledge.get_node(version, key)
        except NodeNotFound:
            facts.append(Fact(kind="test", name=key, value=value))
            continue
        if node.type == "test":
            facts.append(Fact(kind="test", name=str(node.fields.get("name")), value=value))
    return facts


def resolve_history(
    knowledge: KnowledgeService, version: PackVersionRef, items: list[TherapyItem]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Past therapies checked against the pack's drug nodes.

    A drug is known by its generic name or a synonym (a brand, e.g. ``remicade``), or as
    a drug class (``corticosteroid``). Known ones come back as ``{drug, response,
    nodeIds}`` with the pack's own generic or class name; a later item for the same drug
    replaces an earlier one. The rest are returned as ignored names.
    """
    drugs = [
        n
        for n in knowledge.repo.read_nodes(version_id(version.pack, version.number))
        if n.type == "drug"
    ]
    known: dict[str, dict[str, Any]] = {}
    ignored: list[str] = []
    for item in items:
        wanted = normalise_text(item.drug)
        wanted = CLASS_WORDS.get(wanted, wanted)
        by_name = [n for n in drugs if wanted in drug_names(n)]
        by_class = [n for n in drugs if drug_class(n) == wanted]
        if by_name:
            name = str(by_name[0].fields.get("drug"))
            matched = by_name
        elif by_class:
            name = str(by_class[0].fields.get("drugClass"))
            matched = by_class
        else:
            if item.drug not in ignored:
                ignored.append(item.drug)
            continue
        known[normalise_text(name)] = {
            "drug": name,
            "response": item.response,
            "nodeIds": [n.node_id for n in matched],
        }
    return list(known.values()), ignored


def merge_history(
    earlier: list[dict[str, Any]], later: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """An earlier follow-up's history with the new one; the new response wins per drug."""
    merged = {normalise_text(str(h["drug"])): h for h in earlier}
    merged.update({normalise_text(str(h["drug"])): h for h in later})
    return list(merged.values())


def history_facts(history: list[dict[str, Any]]) -> list[Fact]:
    """``therapy`` facts for the walk from the resolved history."""
    return [Fact(kind="therapy", name=str(h["drug"]), value=str(h["response"])) for h in history]


def history_note(history: list[dict[str, Any]], ignored: list[str], text: str) -> str:
    """The fixed confirmation line: pack names and fixed response words, no model text.

    An ignored name is echoed only when the doctor typed it; otherwise it is counted.
    """
    if history:
        parts = [f"{h['drug']} — {RESPONSE_WORDS[str(h['response'])]}" for h in history]
        note = "Noted treatment history: " + "; ".join(parts) + "."
    else:
        note = "No treatment history from the knowledge pack was found in this message."
    typed = normalise_text(text)
    echoed = [name for name in ignored if normalise_text(name) in typed]
    if echoed:
        note += " Not in the knowledge pack, so not used: " + ", ".join(echoed) + "."
    hidden = len(ignored) - len(echoed)
    if hidden:
        note += f" {hidden} other medicine(s) not in the knowledge pack were not used."
    return note


def finding_fields(findings: list[Finding]) -> list[FormField]:
    """The editable chips of a confirm-findings form (AC3.1.1)."""
    return [
        FormField(
            name=f.name,
            label=f.name if f.entered_value is None else f"{f.name} {f.entered_value}",
            kind="finding",
            finding_kind=f.kind,
            value=f.value,
            unit=f.unit,
            duration=f.duration,
            node_id=f.node_id,
            validation_state=f.validation_state,
        )
        for f in findings
    ]


def test_fields(nodes: list[Node]) -> list[FormField]:
    """The fields of a needs-data form: one result per named test (AC3.3.1)."""
    return [
        FormField(
            name=n.node_id,
            label=n.label,
            kind="test_result",
            node_id=n.node_id,
            options=[str(o) for o in n.fields.get("resultOptions", [])],
        )
        for n in nodes
    ]


def case_context(patient: Patient) -> dict[str, Any]:
    """The synthetic patient details the model may use (no name, no ID)."""
    return {
        "synthetic": True,
        "age": patient.age,
        "sex": patient.sex,
        "weightKg": patient.weight_kg,
        "pregnancyStatus": patient.pregnancy_status,
        "comorbidities": patient.comorbidities,
        "allergies": patient.allergies,
        "currentMedication": patient.current_medication,
    }


def dose_note(dose: object) -> dict[str, Any]:
    """The computed dose for this patient, as the model and node detail see it."""
    if isinstance(dose, DoseResult):
        return {"value": dose.value, "unit": dose.unit, "formula": dose.formula}
    return {"missing": "weight needed to compute a per-kg dose"}


def sources_for(
    knowledge: KnowledgeService, version: PackVersionRef, nodes: list[Node]
) -> list[Source]:
    """The sources cited by ``nodes``, in the pack's order."""
    wanted = {s for n in nodes for s in n.source_ids}
    return [s for s in knowledge.sources(version) if s.source_id in wanted]


def build_map(
    knowledge: KnowledgeService, version: PackVersionRef, trav: Traversal, label: str
) -> MapData:
    """Map data for a walk: walked, needed and alternative nodes with their edges."""
    statuses = trav.statuses()
    sub = knowledge.subgraph(version, list(statuses))
    nodes = [
        _map_node(
            n,
            statuses[n.node_id],
            trav.test_results.get(n.node_id),
            trav.tried.get(n.node_id),
        )
        for n in sub.nodes
    ]
    walked = set(trav.walked_edge_ids)
    edges = [
        MapEdge.model_validate(
            {
                "edgeId": e.edge_id,
                "from": e.from_node_id,
                "to": e.to_node_id,
                "style": (
                    "walked"
                    if e.edge_id in walked
                    and statuses.get(e.from_node_id) in TRAVERSED_STATUSES
                    and statuses.get(e.to_node_id) in TRAVERSED_STATUSES
                    else "not_taken"
                ),
            }
        )
        for e in sub.edges
    ]
    return MapData(version=label, nodes=nodes, edges=edges, selected_path=trav.path_node_ids)


def lane_map(
    knowledge: KnowledgeService, version: PackVersionRef, node_ids: list[str]
) -> tuple[list[MapNode], list[MapEdge]]:
    """The nodes and edges of an explore lane, all marked ``exploring``."""
    sub = knowledge.subgraph(version, node_ids)
    nodes = [_map_node(n, "exploring", None) for n in sub.nodes]
    edges = [
        MapEdge.model_validate(
            {"edgeId": e.edge_id, "from": e.from_node_id, "to": e.to_node_id, "style": "exploring"}
        )
        for e in sub.edges
    ]
    return nodes, edges


def with_lanes(base: MapData, lanes: list[tuple[str, list[MapNode], list[MapEdge]]]) -> MapData:
    """Add open explore lanes to a walk's map without changing its main path."""
    present = {n.node_id for n in base.nodes}
    nodes = list(base.nodes)
    edges = list(base.edges)
    for _, lane_nodes, lane_edges in lanes:
        for node in lane_nodes:
            if node.node_id not in present:
                nodes.append(node)
                present.add(node.node_id)
        edges.extend(e for e in lane_edges if e.edge_id not in {x.edge_id for x in edges})
    return base.model_copy(
        update={
            "nodes": nodes,
            "edges": edges,
            "explore_lanes": [
                MapLane(lane_id=lane_id, node_ids=[n.node_id for n in ln])
                for lane_id, ln, _ in lanes
            ],
        }
    )


def _map_node(
    node: Node, status: MapStatus, result: str | None, response: str | None = None
) -> MapNode:
    shown: dict[str, Any] | None = None
    if result is not None:
        shown = {"value": result}
    elif response is not None:
        shown = {"response": response}  # a prior therapy: how it went ("Tried · failed")
    return MapNode(
        node_id=node.node_id,
        type=node.type,
        label=node.label,
        column=node.column,
        status=status,
        result=shown,
    )


def answer_sections(walk: Walk) -> list[dict[str, Any]]:
    """The emitted lines per section in FR4.6 order, then the why (session record shape)."""
    order = {s: i for i, s in enumerate((*SECTION_ORDER, "why"))}
    states: list[SectionState] = sorted(
        (s for s in walk.sections if s.lines), key=lambda s: order.get(s.section_id, 99)
    )
    return [
        {
            "sectionId": s.section_id,
            "title": SECTION_TITLES.get(s.section_id, s.section_id),
            "lines": [{"text": line.text, "nodeIds": line.node_ids} for line in s.lines],
        }
        for s in states
    ]
