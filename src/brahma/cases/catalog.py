"""Lookups over one pack version's nodes by type, for findings and safety (C1 nodes).

A ``NodeCatalog`` is built from the nodes of one immutable version, so it can be cached
by version. Name matching uses U1's ``normalise_text`` (case and surrounding spaces
ignored, BR4.3).
"""

from __future__ import annotations

from brahma.knowledge.errors import NodeNotFound
from brahma.knowledge.matcher import node_names, normalise_text
from brahma.knowledge.models import AllergyCrossReactivityFields, DrugFields, Node


class NodeCatalog:
    """Nodes of one version grouped by type, with name lookups for metrics and drugs."""

    def __init__(self, nodes: list[Node]) -> None:
        self._nodes = {n.node_id: n for n in nodes}
        self._by_type: dict[str, list[Node]] = {}
        for node in sorted(nodes, key=lambda n: n.node_id):
            self._by_type.setdefault(node.type, []).append(node)
        self._metric_names: dict[str, Node] = {}
        for node in self.of_type("metric"):
            for name in node_names(node):
                self._metric_names.setdefault(name, node)
        self._drug_names: dict[str, Node] = {}
        for node in self.of_type("drug"):
            fields = DrugFields.model_validate(node.fields)
            for name in (fields.drug, *fields.synonyms):
                self._drug_names.setdefault(normalise_text(name), node)

    def get(self, node_id: str) -> Node:
        """The node with this ID, or raise NodeNotFound."""
        try:
            return self._nodes[node_id]
        except KeyError:
            raise NodeNotFound(node_id) from None

    def of_type(self, node_type: str) -> list[Node]:
        """Every node of a type, in node-ID order."""
        return list(self._by_type.get(node_type, []))

    def metric(self, name: str) -> Node | None:
        """The metric node whose measure or synonym equals ``name`` (BR2.1)."""
        return self._metric_names.get(normalise_text(name))

    def drug(self, name: str) -> Node | None:
        """The drug node whose drug name or synonym equals ``name``."""
        return self._drug_names.get(normalise_text(name))

    def allergy_nodes(self, allergen: str) -> list[Node]:
        """Allergy cross-reactivity nodes whose allergen class equals ``allergen``."""
        wanted = normalise_text(allergen)
        return [
            n
            for n in self.of_type("allergy_cross_reactivity")
            if normalise_text(AllergyCrossReactivityFields.model_validate(n.fields).allergen_class)
            == wanted
        ]
