"""The benchmark judge (U7, FR13.4-FR13.6): grounded share and pathway agreement.

Both arms are judged by the same claim check the walk guard uses (U1 ``match_claims``):

- graph arm: grounded share comes from the walk's own counts, emitted lines divided by
  emitted plus held-back lines (the guard's verdict distribution).
- plain arm: each recommendation line cites pack sources; it is grounded when it cites
  at least one real pack source and a node under a cited source supports every claim.
  A line with no checkable claims is not a recommendation and stays out of the share.

Agreement compares the nodes behind an arm's lines (cited for the graph arm,
supporting for the plain arm) against the expected pathway nodes.
"""

from __future__ import annotations

from dataclasses import dataclass

from brahma.knowledge.matcher import match_claims
from brahma.knowledge.models import Claim, Node


@dataclass(frozen=True)
class LineVerdict:
    """Whether one plain-arm line is grounded, and the nodes backing it (for agreement)."""

    grounded: bool
    supporting: tuple[str, ...]


def graph_grounded_share(cited: int, held_back: int) -> float | None:
    """The graph arm's grounded share from the walk's counts; None when it wrote nothing."""
    total = cited + held_back
    return cited / total if total else None


def agreement(matched: set[str], expected: set[str]) -> float:
    """Supporting/cited nodes that hit the expected pathway, over expected nodes."""
    return len(matched & expected) / len(expected) if expected else 1.0


def _supports(node: Node, claim: Claim) -> bool:
    return match_claims(node, [claim]).failures == []


def judge_plain_line(
    claims: list[Claim],
    cited_sources: list[str],
    nodes_by_source: dict[str, list[Node]],
    pack_sources: set[str],
    all_nodes: list[Node],
) -> LineVerdict:
    """Judge one plain-arm line (FR13.4): a cited pack source plus a supporting node
    under it for every claim. Supporting nodes are collected pack-wide for agreement."""
    supporting = tuple(
        node.node_id for node in all_nodes if any(_supports(node, claim) for claim in claims)
    )
    if not claims or not cited_sources or any(s not in pack_sources for s in cited_sources):
        return LineVerdict(grounded=False, supporting=supporting)
    candidates = [n for source in cited_sources for n in nodes_by_source.get(source, [])]
    for claim in claims:
        if not any(_supports(node, claim) for node in candidates):
            return LineVerdict(grounded=False, supporting=supporting)
    return LineVerdict(grounded=True, supporting=supporting)
