"""Map data and version labels for replayed sessions and node routes (C8 R-02)."""

from __future__ import annotations

import re

from brahma.agent.models import MapData, MapEdge, MapNode
from brahma.knowledge.models import PackVersionRef
from brahma.server.services import Services

_LABEL = re.compile(r"^([A-Z]{2,5})[ @-](\d+\.\d+)$")


def parse_version(text: str) -> PackVersionRef | None:
    """``"IBD 1.0"``, ``"IBD@1.0"`` or ``"IBD-1.0"`` as a version, else None."""
    match = _LABEL.match(text.strip())
    if match is None:
        return None
    return PackVersionRef(pack=match.group(1), number=match.group(2))


def session_map(shared: Services, session_id: str) -> MapData:
    """The map of a recorded session: the walk's stored map, choices included.

    Falls back to rebuilding the path (all marked as used) when the walk's stored
    map is gone, e.g. data recorded before maps were stored.
    """
    record = shared.audit.get_session(session_id).record
    stored = shared.engine.repo.get(record.walk_id)
    if stored is not None and stored.map is not None:
        return MapData.model_validate(stored.map)
    version = parse_version(record.pack_version)
    if version is None or not record.path_node_ids:
        return MapData(version=record.pack_version, nodes=[], edges=[], selected_path=[])
    sub = shared.knowledge.subgraph(version, record.path_node_ids)
    nodes = [
        MapNode(node_id=n.node_id, type=n.type, label=n.label, column=n.column, status="used")
        for n in sub.nodes
    ]
    edges = [
        MapEdge.model_validate(
            {"edgeId": e.edge_id, "from": e.from_node_id, "to": e.to_node_id, "style": "walked"}
        )
        for e in sub.edges
    ]
    return MapData(
        version=record.pack_version, nodes=nodes, edges=edges, selected_path=record.path_node_ids
    )
