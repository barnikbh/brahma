"""Read-only browsing of a pack's saved nodes for the Knowledge screen (no model, no writes).

``pack_graph`` returns lightweight nodes and edges so the doctor can search and walk the
structure; ``node_view`` returns one node with its sources, comments, connected nodes and
who last updated it. Both use C1 (``KnowledgeService``) reads and U5's provenance.
"""

from __future__ import annotations

from typing import Any

from brahma.knowledge.errors import NodeNotFound, VersionNotFound
from brahma.knowledge.models import Edge, Node, PackVersionRef
from brahma.knowledge.repository import version_id
from brahma.updates.service import UpdateService

_COMPARATORS = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "="}


def resolve_version(service: UpdateService, pack: str, version: str | None) -> PackVersionRef:
    """The named version of a pack, or its live version; VersionNotFound when unknown."""
    if version is None:
        return service.knowledge.live_version(pack)
    if service.knowledge.repo.get_version(pack, version) is None:
        raise VersionNotFound(pack, version)
    return PackVersionRef(pack=pack, number=version)


def relation_label(edge: Edge) -> str:
    """A short readable edge label such as ``refines to`` or ``first line (finding = x)``."""
    label = edge.relation.replace("_", " ")
    if edge.relation == "requires":
        label = f"needs first ({edge.strength or 'must'})"
    condition = edge.condition
    if condition is None:
        return label
    subject = condition.finding or condition.test or condition.therapy or "value"
    return f"{label} ({subject} {_COMPARATORS[condition.comparator]} {condition.value})"


def list_packs(service: UpdateService) -> list[dict[str, Any]]:
    """Each pack with its live version and every version number, newest first."""
    packs = []
    for live in service.knowledge.repo.live_versions():
        header = service.knowledge.repo.get_pack(live.pack)
        packs.append(
            {
                "pack": live.pack,
                "name": header.name if header else live.pack,
                "liveVersion": live.number,
                "versions": [v.number for v in service.knowledge.list_versions(live.pack)],
            }
        )
    return packs


def _initial(service: UpdateService, pack: str) -> str:
    versions = service.knowledge.list_versions(pack)
    return versions[-1].number if versions else "1.0"


def pack_graph(service: UpdateService, pack: str, version: str | None) -> dict[str, Any]:
    """All nodes (ID, type, label, column) and edges of one pack version."""
    ref = resolve_version(service, pack, version)
    key = version_id(ref.pack, ref.number)
    repo = service.knowledge.repo
    updates = service.node_provenance(ref.pack, ref.number)
    return {
        "pack": ref.pack,
        "version": ref.number,
        "initialVersion": _initial(service, ref.pack),
        "nodes": [
            {
                "nodeId": n.node_id,
                "type": n.type,
                "label": n.label,
                "column": n.column,
                "updatedAt": updates[n.node_id].updated_at if n.node_id in updates else None,
            }
            for n in repo.read_nodes(key)
        ],
        "edges": [
            {
                "edgeId": e.edge_id,
                "from": e.from_node_id,
                "to": e.to_node_id,
                "relation": e.relation,
                "label": relation_label(e),
            }
            for e in repo.read_edges(key)
        ],
    }


def _neighbour(node: Node, edge: Edge) -> dict[str, Any]:
    return {
        "edgeId": edge.edge_id,
        "nodeId": node.node_id,
        "type": node.type,
        "label": node.label,
        "relation": edge.relation,
        "relationLabel": relation_label(edge),
    }


def node_view(
    service: UpdateService, pack: str, version: str | None, node_id: str
) -> dict[str, Any]:
    """One node with sources, comments, incoming and outgoing edges and who updated it."""
    ref = resolve_version(service, pack, version)
    key = version_id(ref.pack, ref.number)
    repo = service.knowledge.repo
    nodes = {n.node_id: n for n in repo.read_nodes(key)}
    node = nodes.get(node_id)
    if node is None:
        raise NodeNotFound(node_id)
    edges = repo.read_edges(key)
    sources = [s for s in service.knowledge.sources(ref) if s.source_id in node.source_ids]
    updated = service.node_provenance(ref.pack, ref.number).get(node_id)
    comments = service.knowledge.list_comments(node_id)
    return {
        "node": node.model_dump(mode="json", by_alias=True, exclude={"pack_version"}),
        "sources": [s.model_dump(mode="json", by_alias=True) for s in sources],
        "comments": [c.model_dump(mode="json", by_alias=True) for c in comments],
        "outgoing": [
            _neighbour(nodes[e.to_node_id], e) for e in edges if e.from_node_id == node_id
        ],
        "incoming": [
            _neighbour(nodes[e.from_node_id], e) for e in edges if e.to_node_id == node_id
        ],
        "updated": updated.model_dump(mode="json", by_alias=True) if updated else None,
        "initialVersion": _initial(service, ref.pack),
        "packVersion": f"{ref.pack} {ref.number}",
    }
