"""The grounding guard: ``check_line`` and ``check_line_by_source`` (C6, BR1, FR4.10).

A line's claims are the claims the model declared plus every claim the deterministic
``ClaimScanner`` finds in its text, so a dose cannot be hidden by leaving it out of the
declared claims (BR1.1). Each claim must match a field of a cited node exactly after
unit normalisation (U1 ``match_claims``); a dose for a per-kg drug may also match the
node's per-kg value or the case's computed dose (U3 ``compute_dose``) (BR1.2). A line
passes only when every claim matches and it cites at least one node of the pinned
version (BR1.3). Any exception inside the guard counts as a failed check (NFR8.5).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence

from brahma.agent.models import CheckResult, GuardFailure
from brahma.agent.scanner import ClaimScanner, merge_claims
from brahma.cases.models import DoseResult
from brahma.cases.service import CaseService
from brahma.knowledge.errors import NodeNotFound
from brahma.knowledge.models import Claim, Node, PackVersionRef
from brahma.knowledge.repository import version_id
from brahma.knowledge.service import KnowledgeService
from brahma.knowledge.units import convert, to_decimal

logger = logging.getLogger("brahma.agent.guard")

NO_CITED_NODE = "no_cited_node"
NODE_NOT_IN_VERSION = "node_not_in_version"
NODE_NOT_WALKED = "node_not_walked"
NO_CITED_SOURCE = "no_cited_source"
SOURCE_NOT_IN_PACK = "source_not_in_pack"
NOT_SUPPORTED = "no_supporting_node"
GUARD_ERROR = "guard_error"


class Guard:
    """Checks model-written lines against the walked nodes before anything is shown."""

    def __init__(self, knowledge: KnowledgeService, cases: CaseService) -> None:
        self._knowledge = knowledge
        self._cases = cases
        self.scanner = ClaimScanner(knowledge)

    # --- C6 operations ---------------------------------------------------------------

    def check_line(
        self,
        text: str,
        cited_node_ids: Sequence[str],
        version: PackVersionRef,
        case_id: str | None,
        *,
        declared: Iterable[Claim] = (),
        allowed_node_ids: Iterable[str] | None = None,
    ) -> CheckResult:
        """Check one line against the nodes it cites (BR1.1-BR1.3).

        ``allowed_node_ids``, when given, are the nodes the walk chose for this section:
        a citation outside them fails, because the model never chooses nodes (BR2.2).
        """
        try:
            allowed = set(allowed_node_ids) if allowed_node_ids is not None else None
            return self._check_line(text, list(cited_node_ids), version, case_id, declared, allowed)
        except Exception as exc:
            return self._errored(exc)

    def check_line_by_source(
        self,
        text: str,
        cited_source_ids: Sequence[str],
        version: PackVersionRef,
        case_id: str | None,
        *,
        declared: Iterable[Claim] = (),
    ) -> CheckResult:
        """Check a line that cites sources, not nodes (C6 R-03, BR1.5).

        The line passes only when, for one cited source, a node citing that source
        supports every claim by the same rules as ``check_line``. A line citing no
        source, or a source that is not in the pack, fails.
        """
        try:
            return self._check_by_source(text, list(cited_source_ids), version, case_id, declared)
        except Exception as exc:
            return self._errored(exc)

    # --- internals -------------------------------------------------------------------

    def _claims(self, text: str, version: PackVersionRef, declared: Iterable[Claim]) -> list[Claim]:
        return merge_claims(list(declared), self.scanner.scan(text, version))

    def _check_line(
        self,
        text: str,
        cited: list[str],
        version: PackVersionRef,
        case_id: str | None,
        declared: Iterable[Claim],
        allowed: set[str] | None,
    ) -> CheckResult:
        claims = self._claims(text, version, declared)
        failures: list[GuardFailure] = []
        nodes: list[Node] = []
        for node_id in dict.fromkeys(cited):
            if allowed is not None and node_id not in allowed:
                failures.append(GuardFailure(reason=NODE_NOT_WALKED, node_id=node_id))
                continue
            try:
                nodes.append(self._knowledge.get_node(version, node_id))
            except NodeNotFound:
                failures.append(GuardFailure(reason=NODE_NOT_IN_VERSION, node_id=node_id))
        if not nodes:
            failures.append(GuardFailure(reason=NO_CITED_NODE))
        else:
            failures.extend(self._unmatched(claims, nodes, case_id))
        return CheckResult(passed=not failures, claims=claims, failures=failures)

    def _unmatched(
        self, claims: list[Claim], nodes: list[Node], case_id: str | None
    ) -> list[GuardFailure]:
        failures: list[GuardFailure] = []
        for claim in claims:
            reasons = [self._claim_failure(node, claim, case_id) for node in nodes]
            if all(r is not None for r in reasons):
                failures.append(GuardFailure(claim=claim, reason=str(reasons[0])))
        return failures

    def _claim_failure(self, node: Node, claim: Claim, case_id: str | None) -> str | None:
        """None when ``node`` supports ``claim``, else the failure reason."""
        result = self._knowledge.match_claims(node, [claim])
        if not result.failures:
            return None
        reason = result.failures[0].reason
        if (
            claim.kind == "dose"
            and node.type == "drug"
            and node.fields.get("doseBasis") == "per_kg"
        ):
            return None if self._per_kg_dose_matches(node, claim, case_id) else reason
        return reason

    def _per_kg_dose_matches(self, node: Node, claim: Claim, case_id: str | None) -> bool:
        claimed = to_decimal(claim.value)
        if claimed is None:
            return False
        expected = to_decimal(node.fields.get("doseValue"))
        as_per_kg = convert(claimed, claim.unit, node.fields.get("doseUnit"))
        if expected is not None and as_per_kg is not None and as_per_kg == expected:
            return True
        if case_id is None:
            return False
        dose = self._cases.compute_dose(case_id, node.node_id)
        if not isinstance(dose, DoseResult):
            return False
        as_total = convert(claimed, claim.unit, dose.unit)
        return as_total is not None and as_total == to_decimal(dose.value)

    def _check_by_source(
        self,
        text: str,
        cited: list[str],
        version: PackVersionRef,
        case_id: str | None,
        declared: Iterable[Claim],
    ) -> CheckResult:
        claims = self._claims(text, version, declared)
        if not cited:
            return CheckResult(
                passed=False, claims=claims, failures=[GuardFailure(reason=NO_CITED_SOURCE)]
            )
        known = {s.source_id for s in self._knowledge.sources(version)}
        failures = [
            GuardFailure(reason=SOURCE_NOT_IN_PACK, node_id=s) for s in cited if s not in known
        ]
        if failures:
            return CheckResult(passed=False, claims=claims, failures=failures)
        if not claims:
            return CheckResult(passed=True, claims=claims, failures=[])
        for source_id in dict.fromkeys(cited):
            if self._supported_by_source(version, source_id, claims, case_id):
                return CheckResult(passed=True, claims=claims, failures=[])
        return CheckResult(
            passed=False,
            claims=claims,
            failures=[GuardFailure(claim=c, reason=NOT_SUPPORTED) for c in claims],
        )

    def _supported_by_source(
        self, version: PackVersionRef, source_id: str, claims: list[Claim], case_id: str | None
    ) -> bool:
        if self._knowledge.find_supporting_node(version, source_id, claims) is not None:
            return True
        # Same rules as check_line: a per-kg dose is not an exact U1 field match, so try
        # each node citing the source with the guard's own per-claim rules.
        key = version_id(version.pack, version.number)
        for node in self._knowledge.repo.read_nodes(key):
            if source_id in node.source_ids and all(
                self._claim_failure(node, c, case_id) is None for c in claims
            ):
                return True
        return False

    @staticmethod
    def _errored(exc: Exception) -> CheckResult:
        logger.error(json.dumps({"event": "guard_error", "error": type(exc).__name__}))
        return CheckResult(
            passed=False,
            claims=[],
            failures=[GuardFailure(reason=GUARD_ERROR)],
            error=type(exc).__name__,
        )
