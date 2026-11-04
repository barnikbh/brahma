"""The C1 public interface of the knowledge graph (contract-summary.md C1).

``KnowledgeService`` wires the loader, validator, repository and per-version
``GraphIndex`` cache, and writes one structured JSON log line per ``load_pack`` and
``create_version`` (NFR11.1). Every read names a version (BR1.5).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from brahma.knowledge.db import kg_connect
from brahma.knowledge.errors import (
    KnowledgeError,
    PackLoadError,
    VersionNotFound,
    VersionRequired,
)
from brahma.knowledge.index import GraphIndex
from brahma.knowledge.loader import PackLoader
from brahma.knowledge.matcher import find_supporting_node as _find_supporting_node
from brahma.knowledge.matcher import match_claims as _match_claims
from brahma.knowledge.models import (
    ChangeSet,
    Claim,
    Edge,
    Fact,
    MatchResult,
    Node,
    NodeComment,
    PackHeader,
    PackVersion,
    PackVersionRef,
    RangeResult,
    SearchResult,
    Source,
    Step,
    Subgraph,
)
from brahma.knowledge.repository import KnowledgeRepository, VersionContent, version_id
from brahma.knowledge.validator import PackValidator

logger = logging.getLogger("brahma.knowledge")

SYSTEM_PROFILE_ID = "system"


def _apply_changes(
    nodes: dict[str, Node], edges: dict[str, Edge], changes: ChangeSet
) -> tuple[list[Node], list[Edge]]:
    """Apply a ChangeSet to copies of a base version's nodes and edges."""
    for node in changes.add_nodes:
        if node.node_id in nodes:
            raise PackLoadError(node.node_id, "already exists; use updateNodes")
        nodes[node.node_id] = node
    for node in changes.update_nodes:
        if node.node_id not in nodes:
            raise PackLoadError(node.node_id, "not in the base version")
        nodes[node.node_id] = node
    for node_id in changes.remove_node_ids:
        if nodes.pop(node_id, None) is None:
            raise PackLoadError(node_id, "not in the base version")
    for edge in changes.add_edges:
        if edge.edge_id in edges:
            raise PackLoadError(edge.edge_id, "edge already exists")
        edges[edge.edge_id] = edge
    for edge_id in changes.remove_edge_ids:
        if edges.pop(edge_id, None) is None:
            raise PackLoadError(edge_id, "not in the base version")
    stripped = [n.model_copy(update={"pack_version": None}) for n in nodes.values()]
    return stripped, list(edges.values())


class KnowledgeService:
    """Versioned clinical knowledge: load, version, search, traverse, match and comment."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.repo = KnowledgeRepository(conn)
        self.loader = PackLoader()
        self.validator = PackValidator()
        self._indexes: dict[str, GraphIndex] = {}
        for live in self.repo.live_versions():
            self._build_index(PackVersionRef(pack=live.pack, number=live.number))

    @classmethod
    def open(cls, path: str | Path | None = None) -> KnowledgeService:
        """Open the database at ``path`` (default ``BRAHMA_DB_PATH``) and warm live indexes."""
        return cls(kg_connect(path))

    def close(self) -> None:
        """Close the database connection."""
        self.repo.conn.close()

    # --- writes --------------------------------------------------------------------

    def load_pack(self, path: str | Path, published_by: str = SYSTEM_PROFILE_ID) -> PackVersionRef:
        """Validate a pack file and store it as the pack's new live version (W1, BR1.3).

        Raises PackLoadError (nothing stored) for any invalid content, and
        VersionNotIncreasing when the file's number is not higher than the live one.
        """
        started = time.perf_counter()
        log: dict[str, Any] = {"event": "load_pack", "pack": None, "version": None, "nodes": 0}
        try:
            pack = self.loader.read(path)
            log.update(pack=pack.pack.code, version=pack.version, nodes=len(pack.nodes))
            self.validator.validate(pack.pack.code, pack.sources, pack.nodes, pack.edges)
            content = VersionContent(pack.sources, pack.nodes, pack.edges, pack.change_summary)
            stored = self.repo.publish(pack.pack, content, published_by, number=pack.version)
            ref = PackVersionRef(pack=stored.pack, number=stored.number)
            self._build_index(ref)
        except KnowledgeError as exc:
            self._log(log, started, exc)
            raise
        self._log(log, started, None)
        return ref

    def create_version(
        self, pack: str, base: PackVersionRef, changes: ChangeSet, published_by: str
    ) -> PackVersionRef:
        """Apply a ChangeSet to the live ``base`` and store it as the next minor version (W6).

        The result is re-validated; any failure leaves both versions unchanged. Raises
        BaseNotLive if ``base`` is no longer the live version.
        """
        started = time.perf_counter()
        log: dict[str, Any] = {"event": "create_version", "pack": pack, "version": None}
        try:
            if base.pack != pack:
                raise PackLoadError(pack, f"base version belongs to pack {base.pack}")
            index = self._index(base)
            nodes, edges = _apply_changes(
                dict(index.nodes),
                {e.edge_id: e for es in index.out_edges.values() for e in es},
                changes,
            )
            log["nodes"] = len(nodes)
            sources = self._merge_sources(self.repo.read_sources(pack), changes.add_sources)
            self.validator.validate(pack, sources, nodes, edges)
            header = self._header(pack)
            content = VersionContent(sources, nodes, edges, changes.change_summary)
            stored = self.repo.publish(header, content, published_by, base_number=base.number)
            ref = PackVersionRef(pack=stored.pack, number=stored.number)
            log["version"] = ref.number
            self._build_index(ref)
        except KnowledgeError as exc:
            self._log(log, started, exc)
            raise
        self._log(log, started, None)
        return ref

    def add_comment(self, node_id: str, author_profile_id: str, text: str) -> str:
        """Store a comment on a pack-prefixed node ID and return its ID (BR2.7).

        Raises CommentInvalid for blank or over-long text, NodeNotFound for an unknown node.
        """
        return self.repo.add_comment(node_id, author_profile_id, text)

    # --- version reads ---------------------------------------------------------------

    def live_version(self, pack: str) -> PackVersionRef:
        """The pack's live version; raises VersionNotFound when the pack is unknown."""
        live = self.repo.live_version(pack)
        if live is None:
            raise VersionNotFound(pack)
        return PackVersionRef(pack=live.pack, number=live.number)

    def list_versions(self, pack: str) -> list[PackVersion]:
        """Every version of the pack, newest first, for version history."""
        return self.repo.list_versions(pack)

    def list_comments(self, node_id: str) -> list[NodeComment]:
        """Comments on a node across versions of its pack, newest first."""
        return self.repo.list_comments(node_id)

    # --- graph reads (each names a version) ------------------------------------------

    def get_node(self, version: PackVersionRef, node_id: str) -> Node:
        """One node with its fields and source IDs; raises NodeNotFound."""
        return self._index(version).node(node_id)

    def search(self, version: PackVersionRef, facts: list[Fact]) -> SearchResult:
        """Entry nodes matching the facts by name, synonym and converted value (BR2.1).

        Review-scoped facts never open entries: a day-3 result refines the plan,
        it must not re-diagnose the patient.
        """
        presenting = [f for f in facts if f.context == "presenting"]
        return self._index(version).search(presenting)

    def neighbours(
        self,
        version: PackVersionRef,
        node_id: str,
        facts: list[Fact],
        relation: str | None = None,
    ) -> list[Step]:
        """Outgoing edges of a node as Steps with their status for these facts (BR2.2, BR2.3)."""
        return self._index(version).neighbours(node_id, facts, relation)

    def criterion_targets(self, version: PackVersionRef, node_id: str) -> list[Node]:
        """Tiers a response criterion escalates to when it is met (empty when none).

        A criterion links to a tier only when one of the tiers reviewing it (an
        incoming ``responds_if`` or ``monitor_with`` edge) has an ``escalate_to``
        edge whose condition exactly matches the criterion's own
        measure/threshold/comparator/unit fields. Monitoring nodes, watch-outs
        and prose-only criteria have no wired consequence and link nowhere.
        """
        index = self._index(version)
        _, links = self._criterion_links(version, node_id)
        targets: list[Node] = []
        seen: set[str] = set()
        for _, edge in links:
            if edge.to_node_id not in seen:
                seen.add(edge.to_node_id)
                targets.append(index.node(edge.to_node_id))
        return targets

    def evaluate_criterion(
        self, version: PackVersionRef, node_id: str, value: float
    ) -> tuple[bool, list[Node]]:
        """Whether the recorded review value meets the criterion, and where it leads.

        The value is checked with the real matcher against the linked escalation
        conditions only; anything unwired never meets.
        """
        index = self._index(version)
        node, links = self._criterion_links(version, node_id)
        if not links:
            return False, []
        fields = node.fields
        fact = Fact(
            kind="finding",
            name=str(fields.get("measure")),
            value=value,
            unit=fields.get("unit"),
            context="review",
        )
        targets: list[Node] = []
        seen: set[str] = set()
        for tier, edge in links:
            steps = index.neighbours(tier, [fact], "escalate_to")
            met = any(
                step.edge.edge_id == edge.edge_id and step.status == "followable" for step in steps
            )
            if met and edge.to_node_id not in seen:
                seen.add(edge.to_node_id)
                targets.append(index.node(edge.to_node_id))
        return len(targets) > 0, targets

    def _criterion_links(
        self, version: PackVersionRef, node_id: str
    ) -> tuple[Node, list[tuple[str, Edge]]]:
        """The node plus (tier, escalate edge) pairs matching its criterion fields."""
        index = self._index(version)
        node = index.node(node_id)
        links: list[tuple[str, Edge]] = []
        if node.type != "response_criterion":
            return node, links
        fields = node.fields
        measure, threshold, comparator = (
            fields.get("measure"),
            fields.get("threshold"),
            fields.get("comparator"),
        )
        if (
            not isinstance(measure, str)
            or not measure
            or not isinstance(comparator, str)
            or not comparator
            or threshold is None
        ):
            return node, links
        unit = fields.get("unit")
        tiers = [
            edge.from_node_id
            for edge in index.incoming(node_id)
            if edge.relation in ("responds_if", "monitor_with")
        ]
        for tier in tiers:
            for edge in index.outgoing(tier, "escalate_to"):
                condition = edge.condition
                if (
                    condition is None
                    or condition.finding != measure
                    or str(condition.value) != str(threshold)
                    or condition.comparator != comparator
                    or (condition.unit or None) != (unit or None)
                ):
                    continue
                links.append((tier, edge))
        return node, links

    def reference_range(
        self,
        version: PackVersionRef,
        node_id: str,
        sex: str | None,
        age: float | None,
        pregnancy: bool | None,
    ) -> RangeResult | None:
        """The reference range for a patient, by sex, age band and pregnancy (BR2.4)."""
        return self._index(version).reference_range(node_id, sex, age, pregnancy)

    def sources(self, version: PackVersionRef) -> list[Source]:
        """The sources cited by this version's nodes."""
        return list(self._index(version).sources)

    def match_claims(self, node: Node, claims: Iterable[Claim]) -> MatchResult:
        """Exact claim matching against one node's fields (BR2.5)."""
        return _match_claims(node, claims)

    def find_supporting_node(
        self, version: PackVersionRef, source_id: str, claims: list[Claim]
    ) -> Node | None:
        """The first node citing ``source_id`` that supports every claim, else None (BR2.5)."""
        return _find_supporting_node(self._index(version).nodes_citing(source_id), claims)

    def subgraph(self, version: PackVersionRef, node_ids: list[str]) -> Subgraph:
        """Nodes, the edges among them, and missing IDs, for the map (BR2.6)."""
        return self._index(version).subgraph(node_ids)

    # --- internals -------------------------------------------------------------------

    def _index(self, version: PackVersionRef | None) -> GraphIndex:
        if version is None:
            raise VersionRequired("every read must name a pack version")
        key = version_id(version.pack, version.number)
        index = self._indexes.get(key)
        if index is None:
            if self.repo.get_version(version.pack, version.number) is None:
                raise VersionNotFound(version.pack, version.number)
            index = self._build_index(version)
        return index

    def _build_index(self, version: PackVersionRef) -> GraphIndex:
        key = version_id(version.pack, version.number)
        index = GraphIndex(
            version,
            self.repo.read_nodes(key),
            self.repo.read_edges(key),
            self.repo.read_sources(version.pack),
        )
        self._indexes[key] = index
        return index

    def _header(self, pack: str) -> PackHeader:
        stored = self.repo.get_pack(pack)
        if stored is None:
            raise VersionNotFound(pack)
        return PackHeader(code=stored.code, name=stored.name, specialty=stored.specialty)

    @staticmethod
    def _merge_sources(existing: list[Source], added: list[Source]) -> list[Source]:
        merged = {s.source_id: s for s in existing}
        for source in added:
            if source.source_id in merged and merged[source.source_id] != source:
                raise PackLoadError(source.source_id, "source exists with different details")
            merged[source.source_id] = source
        return list(merged.values())

    @staticmethod
    def _log(entry: dict[str, Any], started: float, error: Exception | None) -> None:
        entry["durationMs"] = round((time.perf_counter() - started) * 1000, 1)
        entry["result"] = "ok" if error is None else "error"
        if error is not None:
            entry["error"] = f"{type(error).__name__}: {error}"
            logger.warning(json.dumps(entry, sort_keys=True))
        else:
            logger.info(json.dumps(entry, sort_keys=True))
