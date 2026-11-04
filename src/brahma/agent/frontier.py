"""The care-loop frontier: what is lit on the map now, recomputed from the case's events.

Deterministic and model-free. The walk's map says what the pathway offers; the events say
what has happened since (a sign present now, a result in, an action done). After each event
this module lights, from the pack's edges only:

* ``requires``: a chosen action's tests are **To do first** until a result is recorded for
  that action (a result from presenting does not count unless the edge says it stays valid
  for some days and it is still inside them);
* ``monitors``: monitoring and response criteria of a chosen action are **Due**, then Done;
* ``watch_for``: watch-outs of a chosen action are **Watch for**; a sign marked present
  becomes **Present** and its ``if_present`` targets light (**Now** for an escalation,
  **Due** for a test or other step; a test due again after the sign is recorded after its
  last result).

The result is the map with these statuses plus any node the events newly brought in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from brahma.agent.models import CareEvent, MapData, MapEdge, MapNode, MapStatus
from brahma.knowledge.models import Edge, Node, PackVersionRef, node_kind
from brahma.knowledge.service import KnowledgeService

# Statuses that mean "look at this now"; newly entering one is what the card is about.
LIT_STATUSES: frozenset[str] = frozenset({"todo_first", "due", "watch", "present", "now"})
MONITOR_TYPES = frozenset({"monitoring", "response_criterion"})


@dataclass
class Frontier:
    """The map after events, plus per-node reasons."""

    data: MapData
    lit: dict[str, MapStatus] = field(default_factory=dict)  # node id -> lit status


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _latest(events: list[CareEvent], node_id: str, kinds: tuple[str, ...]) -> CareEvent | None:
    found = [e for e in events if e.node_id == node_id and e.kind in kinds]
    return found[-1] if found else None


class _Overlay:
    def __init__(self, base: MapData, nodes: dict[str, Node], edges: list[Edge]) -> None:
        self.nodes = {n.node_id: n.model_copy() for n in base.nodes}
        self.edges = {e.edge_id: e.model_copy() for e in base.edges}
        self.pack_nodes = nodes
        self.pack_edges = edges
        self.base = base

    def status(self, node_id: str, status: MapStatus, reason: str | None = None) -> None:
        current = self.nodes.get(node_id)
        if current is None:
            pack = self.pack_nodes[node_id]
            current = MapNode(
                node_id=pack.node_id,
                type=pack.type,
                label=pack.label,
                column=pack.column,
                status=status,
                kind=node_kind(pack.type),
                pos=list(pack.pos) if pack.pos else None,
            )
        self.nodes[node_id] = current.model_copy(update={"status": status, "reason": reason})

    def result(self, node_id: str, value: str) -> None:
        current = self.nodes[node_id]
        self.nodes[node_id] = current.model_copy(update={"result": {"value": value}})

    def edge(self, edge: Edge, style: str = "walked") -> None:
        if edge.from_node_id in self.nodes and edge.to_node_id in self.nodes:
            self.edges[edge.edge_id] = MapEdge.model_validate(
                {
                    "edgeId": edge.edge_id,
                    "from": edge.from_node_id,
                    "to": edge.to_node_id,
                    "style": style,
                    "relation": edge.relation,
                }
            )


def apply_events(
    knowledge: KnowledgeService,
    version: PackVersionRef,
    base: MapData,
    events: list[CareEvent],
) -> Frontier:
    """The base map with the care-loop statuses the events produce."""
    from brahma.knowledge.repository import version_id

    pack_edges = knowledge.repo.read_edges(version_id(version.pack, version.number))
    pack_nodes = {
        n.node_id: n for n in knowledge.repo.read_nodes(version_id(version.pack, version.number))
    }
    ov = _Overlay(base, pack_nodes, pack_edges)
    by_source: dict[str, list[Edge]] = {}
    for edge in pack_edges:
        by_source.setdefault(edge.from_node_id, []).append(edge)
    for drawn in base.edges:  # relation labels for the edges the walk already drew
        match = next((e for e in pack_edges if e.edge_id == drawn.edge_id), None)
        if match is not None:
            ov.edges[drawn.edge_id] = drawn.model_copy(update={"relation": match.relation})

    chosen = [n.node_id for n in base.nodes if n.status == "chosen"]
    # Everything a chosen action lights comes from its own tier and its own edges.
    for action in chosen:
        _light_requirements(ov, by_source, events, action)
    for current in list(ov.nodes.values()):
        _light_after_choice(ov, current, bool(chosen))
    for event in events:
        if event.node_id not in ov.nodes:
            continue
        if event.kind == "present":
            _present(ov, by_source, events, event)
        elif event.for_node_id is None or event.for_node_id in chosen:
            _recorded(ov, event)
    data = base.model_copy(
        update={"nodes": list(ov.nodes.values()), "edges": list(ov.edges.values())}
    )
    lit = {n.node_id: n.status for n in data.nodes if n.status in LIT_STATUSES}
    return Frontier(data=data, lit=lit)


def _light_requirements(
    ov: _Overlay, by_source: dict[str, list[Edge]], events: list[CareEvent], action: str
) -> None:
    label = ov.pack_nodes[action].label
    for edge in by_source.get(action, []):
        if edge.relation != "requires":
            continue
        test = edge.to_node_id
        if test not in ov.pack_nodes:
            continue
        ov.status(test, "todo_first", f"{edge.strength or 'must'} be done before {label}")
        ov.edge(edge)
        scoped = [
            e
            for e in events
            if e.node_id == test and e.kind == "result" and e.for_node_id == action
        ]
        recent = _valid_result(events, test, edge.valid_for_days)
        found = scoped[-1] if scoped else recent
        if found is not None and found.value:
            ov.status(test, "done", f"Result recorded before {label}")
            ov.result(test, found.value)


def _valid_result(events: list[CareEvent], test: str, days: int | None) -> CareEvent | None:
    if days is None:
        return None
    latest = _latest(events, test, ("result",))
    if latest is None:
        return None
    return (
        latest
        if _when(latest.created_at)
        >= datetime.now(tz=_when(latest.created_at).tzinfo) - timedelta(days=days)
        else None
    )


def _light_after_choice(ov: _Overlay, node: MapNode, chosen: bool) -> None:
    """Monitoring and watch-outs the walk lit (status ``used``) after a choice."""
    if node.status != "used":
        return
    if node.type in MONITOR_TYPES and chosen:
        ov.status(node.node_id, "due", "Starts once the treatment is chosen")
    elif node.type in ("watch_out", "escalation"):
        ov.status(node.node_id, "watch")


def _present(
    ov: _Overlay, by_source: dict[str, list[Edge]], events: list[CareEvent], event: CareEvent
) -> None:
    ov.status(event.node_id, "present")
    for edge in by_source.get(event.node_id, []):
        if edge.relation != "if_present" or edge.to_node_id not in ov.pack_nodes:
            continue
        target = ov.pack_nodes[edge.to_node_id]
        ov.status(edge.to_node_id, "now" if target.type == "escalation" else "due")
        ov.nodes[edge.to_node_id] = ov.nodes[edge.to_node_id].model_copy(
            update={"reason": f"Because {ov.pack_nodes[event.node_id].label} is present"}
        )
        ov.edge(edge)
        if target.type == "test":
            newer = [
                e
                for e in events
                if e.node_id == target.node_id
                and e.kind == "result"
                and e.created_at >= event.created_at
            ]
            if newer and newer[-1].value:
                ov.status(target.node_id, "done")
                ov.result(target.node_id, newer[-1].value)


def _recorded(ov: _Overlay, event: CareEvent) -> None:
    """A recorded result or a step marked done means it happened: Done, with the value."""
    if event.kind == "result" and event.value:
        ov.result(event.node_id, event.value)
    ov.status(event.node_id, "done")
