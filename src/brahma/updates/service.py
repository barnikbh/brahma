"""``UpdateService``: proposals, reviewer publishing, history and source checks (U5).

It uses C1 (``KnowledgeService``) for nodes and versions, C2 (U2's ``AuditRepository`` on
the shared connection) for the audit, C3 (``IdentityService.require_role``) for the
reviewer check and C4 (``ModelGateway``, through ``Drafter``) for drafting.

Nothing becomes live without a reviewer: only ``publish`` calls ``create_version``.
A reject writes its status change and its ``proposal_rejected`` entry in one
transaction; a publish writes ``proposal_published`` right after ``create_version``
succeeds (security-design.md NFR7.1). Doctor and drafted proposals write
``proposal_created`` with the proposer; a ``scheduled`` proposal has no human proposer
(it is stored under the ``system`` ID) and is traced by its ``up_source_check_run`` row
instead, since the audit only accepts seeded profiles. Logs carry IDs and error classes.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from brahma.knowledge.errors import BaseNotLive, KnowledgeError
from brahma.knowledge.models import ChangeSet, Edge, Node, PackVersionRef, Source, parse_version
from brahma.knowledge.repository import version_id
from brahma.knowledge.service import SYSTEM_PROFILE_ID, KnowledgeService, _apply_changes
from brahma.knowledge.validator import iter_strings
from brahma.platform.audit.models import AuditEntryIn
from brahma.platform.audit.repository import AuditRepository
from brahma.platform.base import new_id, utc_now
from brahma.platform.db import transaction
from brahma.platform.errors import ConfigError, ProfileNotFound
from brahma.platform.identity import IdentityService
from brahma.platform.models import ModelGateway
from brahma.platform.profiles import ProfileRepository, Role
from brahma.updates.copycheck import CopyChecker, best_passage
from brahma.updates.db import up_connect
from brahma.updates.drafter import Drafter
from brahma.updates.errors import (
    CopyFlagged,
    DraftFailed,
    ProposalClosed,
    ProposalInvalid,
    ProposalNotFound,
    UpdateError,
)
from brahma.updates.fetch import SafeFetcher
from brahma.updates.models import (
    MAX_COMMENT_LENGTH,
    DraftedChanges,
    FetchedSource,
    LinkedSource,
    NodeProvenance,
    Proposal,
    ProposalChange,
    ProposalIn,
    ProposalOrigin,
    ProposalStatus,
    SourceCheckRun,
    VersionHistoryEntry,
)
from brahma.updates.repository import UpdateRepository

logger = logging.getLogger("brahma.updates")

REVIEWER_ROLE: Role = "reviewer"
_FIXED_NODE_KEYS = frozenset({"nodeId", "node_id", "type", "packVersion", "pack_version"})

GatewaySource = ModelGateway | Callable[[], ModelGateway] | None


def target_version(base_number: str) -> str:
    """The draft label for the next minor version: ``"1.3"`` -> ``"1.4 draft"``."""
    major, minor = parse_version(base_number)
    return f"{major}.{minor + 1} draft"


def _node_dict(node: Node) -> dict[str, Any]:
    return node.model_dump(mode="json", by_alias=True, exclude={"pack_version"})


def _pack_label(ref: PackVersionRef) -> str:
    return f"{ref.pack} {ref.number}"


def _changed_strings(before: dict[str, Any] | None, after: dict[str, Any]) -> list[str]:
    """The strings in ``after`` that are new, so text already in the node is not re-flagged."""
    old = set(iter_strings(before)) if before is not None else set()
    return [s for s in iter_strings(after) if s not in old]


def _clean_comment(comment: str | None, *, required: bool) -> str | None:
    text = " ".join((comment or "").split())
    if not text:
        if required:
            raise ProposalInvalid("a comment is required")
        return None
    if len(text) > MAX_COMMENT_LENGTH:
        raise ProposalInvalid(f"the comment is longer than {MAX_COMMENT_LENGTH} characters")
    return text


class UpdateService:
    """Knowledge updates (contract C9). See the module docstring."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        knowledge: KnowledgeService,
        identity: IdentityService,
        *,
        fetcher: SafeFetcher | None = None,
        gateway: GatewaySource = None,
    ) -> None:
        """``conn`` must hold the ``pf_`` and ``up_`` tables (see ``up_connect``).

        ``gateway`` is a ``ModelGateway`` or a function that builds one on first use, so
        the service starts without model configuration and drafting reports it clearly.
        """
        self._conn = conn
        self._repo = UpdateRepository(conn)
        self._audit = AuditRepository(conn)
        self._profiles = ProfileRepository(conn)
        self._knowledge = knowledge
        self._identity = identity
        self._fetcher = fetcher or SafeFetcher()
        self._gateway_source = gateway
        self._drafter: Drafter | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """The shared connection (for the conversation service's transactions)."""
        return self._conn

    @property
    def repo(self) -> UpdateRepository:
        """The ``up_`` repository."""
        return self._repo

    @property
    def knowledge(self) -> KnowledgeService:
        """The C1 service this one reads and publishes through."""
        return self._knowledge

    def display_name(self, profile_id: str | None) -> str | None:
        """A profile's display name; the ID itself for unknown ones such as ``seed``."""
        if profile_id is None:
            return None
        profile = self._profiles.get(profile_id)
        return profile.display_name if profile is not None else profile_id

    def require_profile(self, profile_id: str) -> None:
        """Raise ProfileNotFound unless this is a known profile."""
        self._require_profile(profile_id)

    def fetch(self, url: str) -> FetchedSource:
        """Fetch a source page safely (SSRF rules in ``SafeFetcher``)."""
        return self._fetcher.fetch(url)

    def gateway(self) -> ModelGateway:
        """The model gateway, built on first use; DraftFailed when none is configured."""
        return self._drafter_or_fail().gateway

    @classmethod
    def open(cls, path: str | Path | None = None) -> UpdateService:
        """Open ``BRAHMA_DB_PATH`` (or ``path``); the gateway is built from the environment."""
        conn = up_connect(path)
        identity = IdentityService(conn)
        return cls(
            conn,
            KnowledgeService.open(path),
            identity,
            gateway=lambda: ModelGateway.from_env(conn),
        )

    def close(self) -> None:
        """Close the update connection and the knowledge service."""
        self._conn.close()
        self._knowledge.close()

    # --- W1 suggest --------------------------------------------------------------------

    def create_proposal(self, proposal: ProposalIn, proposer_profile_id: str) -> Proposal:
        """Store a doctor's proposal as ``proposed`` against the live version (BR1.1, BR1.2).

        When ``sourceUrl`` is given the page is fetched safely and linked (BR2), and the
        copy check runs against it and the quoted section (BR2.3). Raises ProfileNotFound,
        VersionNotFound, NodeNotFound, ProposalInvalid, PackLoadError (the change does not
        validate) and SourceFetchError. Nothing is stored when any of them is raised.
        """
        self._require_profile(proposer_profile_id)
        base = self._knowledge.live_version(proposal.pack)
        node = self._knowledge.get_node(base, proposal.node_id)
        before = _node_dict(node)
        after_node = self._apply_node_change(node, before, proposal.change)
        changes = ChangeSet(update_nodes=[after_node], change_summary=proposal.comment)
        self._dry_run(base, changes)
        fetched = self._fetcher.fetch(proposal.source_url) if proposal.source_url else None
        after = _node_dict(after_node)
        source_text = "\n".join(
            t for t in (fetched.text if fetched else None, proposal.section) if t
        )
        checker = CopyChecker(source_text)
        flagged = any(checker.is_copy(s) for s in _changed_strings(before, after))
        passage = proposal.section or (
            best_passage(fetched.text, " ".join(_changed_strings(before, after)))
            if fetched
            else None
        )
        change = ProposalChange(
            node_id=node.node_id,
            before=before,
            after=after,
            source_passage=passage,
            copy_flag=flagged,
        )
        sources = [fetched] if fetched else []
        return self._store(base, "doctor", proposer_profile_id, changes, [change], sources)

    # --- W2 draft from a source --------------------------------------------------------

    def draft_from_source(self, pack: str, url: str, proposer_profile_id: str) -> Proposal:
        """Fetch a source, draft node updates with the model and store them (BR2, BR3).

        Raises SourceFetchError, DraftFailed (model failure, invalid output, unknown node
        or no changes) and PackLoadError; no proposal is stored when any is raised.
        """
        self._require_profile(proposer_profile_id)
        base = self._knowledge.live_version(pack)
        fetched = self._fetcher.fetch(url)
        drafted = self._draft(base, fetched)
        if drafted is None:
            raise DraftFailed("the model proposed no changes for this source")
        changes, rows = drafted
        return self._store(base, "drafted", proposer_profile_id, changes, rows, [fetched])

    def store_conversation_proposal(
        self,
        base: PackVersionRef,
        proposer_profile_id: str,
        rows: list[ProposalChange],
        updated: list[Node],
        summary: str,
        sources: list[FetchedSource],
        *,
        added: list[Node] | None = None,
        edges: list[Edge] | None = None,
        new_sources: list[Source] | None = None,
    ) -> Proposal:
        """Store one proposal holding the conversation's node-by-node changes (origin drafted).

        ``added``, ``edges`` and ``new_sources`` carry new nodes, their links into the graph
        and the pack sources they cite. Dry-run validates the combined change on ``base``;
        raises PackLoadError when it does not validate. Nothing is stored then.
        """
        changes = ChangeSet(
            add_nodes=added or [],
            update_nodes=updated,
            add_edges=edges or [],
            add_sources=new_sources or [],
            change_summary=summary,
        )
        self._dry_run(base, changes)
        return self._store(base, "drafted", proposer_profile_id, changes, rows, sources)

    # --- W3 review ---------------------------------------------------------------------

    def get_proposal(self, proposal_id: str) -> Proposal:
        """The proposal with before and after values, passages and copy flags."""
        proposal = self._repo.get_proposal(proposal_id)
        if proposal is None:
            raise ProposalNotFound(proposal_id)
        return proposal

    def list_proposals(
        self, pack: str | None = None, status: ProposalStatus | None = None
    ) -> list[Proposal]:
        """Proposals newest first, optionally filtered by pack and status."""
        return self._repo.list_proposals(pack, status)

    def publish(
        self, proposal_id: str, reviewer_profile_id: str, comment: str | None = None
    ) -> Proposal:
        """Publish a proposal as the pack's next live version (BR1.3-BR1.5).

        Raises Forbidden (not a reviewer), ProposalNotFound, ProposalClosed, CopyFlagged,
        and PackLoadError when the change no longer validates on the live version; the
        proposal then stays ``proposed``. If the base is no longer live, the change set is
        re-applied to the current live version.
        """
        self._identity.require_role(reviewer_profile_id, REVIEWER_ROLE)
        review_comment = _clean_comment(comment, required=False)
        proposal = self._open_proposal(proposal_id)
        flagged = proposal.copy_flagged_node_ids
        if flagged:
            raise CopyFlagged(proposal_id, flagged)
        new_ref, base = self._create_version(proposal, reviewer_profile_id)
        with transaction(self._conn):
            self._repo.set_status(
                proposal_id, "published", reviewer_profile_id, review_comment, new_ref.number
            )
            self._audit.add_entry(
                AuditEntryIn(
                    kind="proposal_published",
                    profile_id=reviewer_profile_id,
                    pack_version=_pack_label(new_ref),
                    payload={
                        "proposalId": proposal_id,
                        "baseVersion": proposal.base_version,
                        "appliedTo": base.number,
                        "rebased": base.number != proposal.base_version,
                        "publishedVersion": new_ref.number,
                        "nodeIds": [c.node_id for c in proposal.changes],
                        "comment": review_comment,
                    },
                )
            )
        event = {"event": "proposal_published", "proposalId": proposal_id}
        logger.info(json.dumps({**event, "version": _pack_label(new_ref)}))
        return self.get_proposal(proposal_id)

    def reject(self, proposal_id: str, reviewer_profile_id: str, comment: str) -> Proposal:
        """Reject a proposal with the reviewer's comment (BR1.6).

        The status change and ``proposal_rejected`` are written in one transaction.
        Raises Forbidden, ProposalNotFound, ProposalClosed and ProposalInvalid (no comment).
        """
        self._identity.require_role(reviewer_profile_id, REVIEWER_ROLE)
        review_comment = _clean_comment(comment, required=True)
        proposal = self._open_proposal(proposal_id)
        with transaction(self._conn):
            self._repo.set_status(proposal_id, "rejected", reviewer_profile_id, review_comment)
            self._audit.add_entry(
                AuditEntryIn(
                    kind="proposal_rejected",
                    profile_id=reviewer_profile_id,
                    pack_version=f"{proposal.pack} {proposal.base_version}",
                    payload={"proposalId": proposal_id, "comment": review_comment},
                )
            )
        return self.get_proposal(proposal_id)

    # --- W4 history --------------------------------------------------------------------

    def version_history(self, pack: str) -> list[VersionHistoryEntry]:
        """Live and superseded versions (C1) merged with proposed and rejected proposals.

        Newest first (BR1.7). A version published from a proposal carries its review
        comment and proposal ID.
        """
        proposals = self._repo.list_proposals(pack)
        by_version = {p.published_version: p for p in proposals if p.published_version}
        entries = [
            VersionHistoryEntry(
                version=v.number,
                status=v.status,
                date=v.published_at,
                author=v.published_by,
                author_name=self.display_name(v.published_by) or v.published_by,
                change=v.change_summary,
                comment=by_version[v.number].review_comment if v.number in by_version else None,
                proposal_id=by_version[v.number].proposal_id if v.number in by_version else None,
            )
            for v in self._knowledge.list_versions(pack)
        ]
        entries += [
            VersionHistoryEntry(
                version=p.target_version,
                status="proposed" if p.status == "proposed" else "rejected",
                date=p.decided_at or p.created_at,
                author=p.proposer_profile_id,
                author_name=self.display_name(p.proposer_profile_id) or p.proposer_profile_id,
                change=p.comment,
                comment=p.review_comment,
                proposal_id=p.proposal_id,
            )
            for p in proposals
            if p.status != "published"
        ]
        return sorted(entries, key=lambda e: e.date, reverse=True)

    def node_provenance(self, pack: str, version_number: str) -> dict[str, NodeProvenance]:
        """Per node, the latest published proposal change at or below ``version_number``.

        Nodes never updated are absent: the caller shows "Initial pack". The proposer is
        who updated it; the reviewer is who published it (decided_at is the time).
        """
        limit = parse_version(version_number)
        found: dict[str, NodeProvenance] = {}
        for row in self._repo.published_node_changes(pack):
            published = row["published_version"]
            if parse_version(published) > limit:
                continue
            proposer, reviewer = row["proposer_profile_id"], row["reviewer_profile_id"]
            found[row["node_id"]] = NodeProvenance(
                node_id=row["node_id"],
                updated_by=proposer,
                updated_by_name=self.display_name(proposer) or proposer,
                approved_by=reviewer,
                approved_by_name=self.display_name(reviewer) or reviewer,
                updated_at=row["decided_at"],
                version=published,
                proposal_id=row["proposal_id"],
            )
        return found

    # --- W5 scheduled check ------------------------------------------------------------

    def check_sources(self) -> SourceCheckRun:
        """Re-fetch every linked source; draft a ``scheduled`` proposal when one changed.

        A failing source is logged (source ID and error class only), marked ``failed``
        and recorded in the run's errors; the run carries on with the next one (BR4.1).
        """
        started = utc_now()
        checked = changed = 0
        errors: list[dict[str, str]] = []
        for source in self._repo.list_linked_sources():
            checked += 1
            try:
                changed += self._check_one(source)
            except (UpdateError, KnowledgeError) as exc:
                label = exc.log_label() if isinstance(exc, UpdateError) else type(exc).__name__
                errors.append({"sourceId": source.source_id, "error": label})
                failure = {"event": "source_check_failed", "sourceId": source.source_id}
                logger.warning(json.dumps({**failure, "error": label}))
                with transaction(self._conn):
                    self._repo.update_source_check(source.source_id, "failed")
        run = SourceCheckRun(
            run_id=new_id("scr"),
            started_at=started,
            finished_at=utc_now(),
            checked=checked,
            changed=changed,
            failed=len(errors),
            errors=errors,
        )
        with transaction(self._conn):
            self._repo.insert_check_run(run)
        logger.info(json.dumps({"event": "source_check_run", **run.model_dump(exclude={"errors"})}))
        return run

    def _check_one(self, source: LinkedSource) -> int:
        """Check one source; return 1 when it changed, else 0."""
        fetched = self._fetcher.fetch(source.url)
        if source.content_hash is None or fetched.content_hash == source.content_hash:
            with transaction(self._conn):
                self._repo.update_source_check(source.source_id, "ok", fetched.content_hash)
            return 0
        base = self._knowledge.live_version(source.pack)
        drafted = self._draft(base, fetched)
        with transaction(self._conn):
            if drafted is not None:
                changes, rows = drafted
                proposal = self._new_proposal(
                    base, "scheduled", SYSTEM_PROFILE_ID, changes, rows, source.source_id
                )
                self._repo.insert_proposal(proposal)
            self._repo.update_source_check(source.source_id, "changed", fetched.content_hash)
        return 1

    # --- internals ---------------------------------------------------------------------

    def _require_profile(self, profile_id: str) -> None:
        if self._profiles.get(profile_id) is None:
            raise ProfileNotFound(profile_id)

    def _open_proposal(self, proposal_id: str) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        if proposal.status != "proposed":
            raise ProposalClosed(proposal_id, proposal.status)
        return proposal

    @staticmethod
    def _apply_node_change(node: Node, before: dict[str, Any], change: dict[str, Any]) -> Node:
        fixed = sorted(set(change) & _FIXED_NODE_KEYS)
        if fixed:
            raise ProposalInvalid(f"these node keys cannot change: {', '.join(fixed)}")
        try:
            after = Node.model_validate({**before, **change})
        except ValidationError as exc:
            names = sorted({str(e["loc"][0]) for e in exc.errors() if e["loc"]})
            raise ProposalInvalid(
                f"the change does not fit node {node.node_id}: {', '.join(names) or 'change'}"
            ) from exc
        if _node_dict(after) == before:
            raise ProposalInvalid(f"the change leaves node {node.node_id} as it is")
        return after

    def _dry_run(self, base: PackVersionRef, changes: ChangeSet) -> None:
        """Validate ``changes`` on ``base`` with U1's validator without storing anything."""
        key = version_id(base.pack, base.number)
        repo = self._knowledge.repo
        nodes, edges = _apply_changes(
            {n.node_id: n for n in repo.read_nodes(key)},
            {e.edge_id: e for e in repo.read_edges(key)},
            changes,
        )
        sources = KnowledgeService._merge_sources(repo.read_sources(base.pack), changes.add_sources)
        self._knowledge.validator.validate(base.pack, sources, nodes, edges)

    def _drafter_or_fail(self) -> Drafter:
        if self._drafter is None:
            source = self._gateway_source
            if source is None:
                raise DraftFailed("no model provider is configured")
            try:
                gateway = source if isinstance(source, ModelGateway) else source()
            except ConfigError as exc:
                raise DraftFailed(str(exc), cause_label="ConfigError") from exc
            self._drafter = Drafter(gateway)
        return self._drafter

    def _draft(
        self, base: PackVersionRef, fetched: FetchedSource
    ) -> tuple[ChangeSet, list[ProposalChange]] | None:
        """Draft, build and dry-run validate node updates; None when nothing changes."""
        nodes = self._knowledge.repo.read_nodes(version_id(base.pack, base.number))
        drafted = self._drafter_or_fail().draft(base, nodes, fetched)
        if not drafted.changes:
            return None
        updated = self._drafted_nodes({n.node_id: n for n in nodes}, drafted)
        changes = ChangeSet(update_nodes=updated, change_summary=drafted.summary)
        self._dry_run(base, changes)
        checker = CopyChecker(fetched.text)
        by_id = {n.node_id: n for n in nodes}
        rows = []
        for node in updated:
            before, after = _node_dict(by_id[node.node_id]), _node_dict(node)
            new_text = _changed_strings(before, after)
            rows.append(
                ProposalChange(
                    node_id=node.node_id,
                    before=before,
                    after=after,
                    source_passage=best_passage(fetched.text, " ".join(new_text)),
                    copy_flag=any(checker.is_copy(s) for s in new_text),
                )
            )
        return changes, rows

    @staticmethod
    def _drafted_nodes(nodes: dict[str, Node], drafted: DraftedChanges) -> list[Node]:
        updated: list[Node] = []
        for change in drafted.changes:
            fields: dict[str, Any] = {"content": change.content}
            if change.label:
                fields["label"] = change.label
            try:
                updated.append(Node.model_validate({**_node_dict(nodes[change.node_id]), **fields}))
            except ValidationError as exc:
                raise DraftFailed(
                    f"the drafted change to {change.node_id} is not a valid node",
                    "ValidationError",
                ) from exc
        return updated

    def _new_proposal(
        self,
        base: PackVersionRef,
        origin: ProposalOrigin,
        proposer: str,
        changes: ChangeSet,
        rows: Iterable[ProposalChange],
        source_id: str | None,
    ) -> Proposal:
        return Proposal(
            proposal_id=new_id("pr"),
            pack=base.pack,
            base_version=base.number,
            target_version=target_version(base.number),
            proposer_profile_id=proposer,
            origin=origin,
            change_set=changes,
            comment=changes.change_summary,
            status="proposed",
            source_id=source_id,
            created_at=utc_now(),
            changes=list(rows),
        )

    def _store(
        self,
        base: PackVersionRef,
        origin: ProposalOrigin,
        proposer: str,
        changes: ChangeSet,
        rows: list[ProposalChange],
        sources: list[FetchedSource],
    ) -> Proposal:
        """Link the sources, insert the proposal and its audit entry in one go."""
        with transaction(self._conn):
            linked = [
                self._repo.upsert_linked_source(base.pack, f.url, f.title, f.content_hash).source_id
                for f in sources
            ]
            source_id = linked[0] if linked else None
            proposal = self._new_proposal(base, origin, proposer, changes, rows, source_id)
            self._repo.insert_proposal(proposal)
            self._audit.add_entry(
                AuditEntryIn(
                    kind="proposal_created",
                    profile_id=proposer,
                    pack_version=_pack_label(base),
                    payload={
                        "proposalId": proposal.proposal_id,
                        "origin": origin,
                        "nodeIds": [r.node_id for r in rows],
                        "copyFlagged": proposal.copy_flagged_node_ids,
                    },
                )
            )
        return proposal

    def _create_version(
        self, proposal: Proposal, reviewer_profile_id: str
    ) -> tuple[PackVersionRef, PackVersionRef]:
        """Call C1 ``create_version`` on the current live version; retry once if it moved."""
        for attempt in (1, 2):
            base = self._knowledge.live_version(proposal.pack)
            try:
                ref = self._knowledge.create_version(
                    proposal.pack, base, proposal.change_set, reviewer_profile_id
                )
            except BaseNotLive:
                if attempt == 2:
                    raise
                continue
            return ref, base
        raise AssertionError("unreachable: the loop returns or raises")  # pragma: no cover
