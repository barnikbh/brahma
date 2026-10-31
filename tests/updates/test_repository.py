"""UpdateRepository SQL (plan Step 6; US8.1, US8.2)."""

from __future__ import annotations

import sqlite3

import pytest

from brahma.knowledge.models import ChangeSet
from brahma.platform.base import utc_now
from brahma.platform.db import transaction
from brahma.updates.errors import ProposalClosed, ProposalNotFound
from brahma.updates.models import Proposal, ProposalChange, SourceCheckRun
from brahma.updates.repository import UpdateRepository


def _proposal(proposal_id: str, pack: str = "IBD", source_id: str | None = None) -> Proposal:
    return Proposal(
        proposal_id=proposal_id,
        pack=pack,
        base_version="1.0",
        target_version="1.1 draft",
        proposer_profile_id="p-maya",
        origin="doctor",
        change_set=ChangeSet(change_summary="Clarify wording"),
        comment="Clarify wording",
        status="proposed",
        source_id=source_id,
        created_at=utc_now(),
        changes=[
            ProposalChange(
                node_id="IBD-N36",
                before={"content": "old"},
                after={"content": "new"},
                source_passage="a synthetic passage",
                copy_flag=True,
            ),
            ProposalChange(node_id="IBD-N37", before=None, after={"content": "added"}),
        ],
    )


@pytest.fixture
def repo(conn: sqlite3.Connection) -> UpdateRepository:
    return UpdateRepository(conn)


def test_a_proposal_round_trips_with_its_changes_in_order(
    conn: sqlite3.Connection, repo: UpdateRepository
) -> None:
    with transaction(conn):
        source = repo.upsert_linked_source("IBD", "https://x.example.org/a", "A", "h1")
        repo.insert_proposal(_proposal("pr-1", source_id=source.source_id))
    stored = repo.get_proposal("pr-1")
    assert stored is not None
    expected = _proposal("pr-1", source_id=source.source_id)
    assert stored == expected.model_copy(update={"created_at": stored.created_at})
    assert [c.node_id for c in stored.changes] == ["IBD-N36", "IBD-N37"]
    assert stored.copy_flagged_node_ids == ["IBD-N36"]
    assert stored.changes[1].before is None
    assert repo.get_proposal("pr-missing") is None


def test_listing_filters_by_pack_and_status(
    conn: sqlite3.Connection, repo: UpdateRepository
) -> None:
    with transaction(conn):
        repo.insert_proposal(_proposal("pr-1"))
        repo.insert_proposal(_proposal("pr-2"))
        repo.insert_proposal(_proposal("pr-3", pack="URO"))
        repo.set_status("pr-2", "rejected", "p-reviewer", "not supported")
    assert [p.proposal_id for p in repo.list_proposals()] == ["pr-3", "pr-2", "pr-1"]
    assert [p.proposal_id for p in repo.list_proposals(pack="IBD")] == ["pr-2", "pr-1"]
    assert [p.proposal_id for p in repo.list_proposals("IBD", "proposed")] == ["pr-1"]
    rejected = repo.list_proposals(status="rejected")[0]
    assert rejected.review_comment == "not supported"
    assert rejected.decided_at is not None


def test_a_status_change_on_a_closed_or_unknown_proposal_is_refused(
    conn: sqlite3.Connection, repo: UpdateRepository
) -> None:
    with transaction(conn):
        repo.insert_proposal(_proposal("pr-1"))
        repo.set_status("pr-1", "published", "p-reviewer", None, "1.1")
    with pytest.raises(ProposalClosed) as closed:
        repo.set_status("pr-1", "rejected", "p-reviewer", "too late")
    assert closed.value.status == "published"
    with pytest.raises(ProposalNotFound):
        repo.set_status("pr-missing", "rejected", "p-reviewer", "x")
    with pytest.raises(ValueError):
        repo.set_status("pr-1", "proposed", "p-reviewer", None)
    stored = repo.get_proposal("pr-1")
    assert stored is not None
    assert (stored.status, stored.published_version) == ("published", "1.1")


def test_linked_source_upsert_keeps_one_row_per_pack_and_url(
    conn: sqlite3.Connection, repo: UpdateRepository
) -> None:
    with transaction(conn):
        first = repo.upsert_linked_source("IBD", "https://x.example.org/a", "A", "h1")
        again = repo.upsert_linked_source("IBD", "https://x.example.org/a", "A2", "h2")
        repo.update_source_check(first.source_id, "failed")
    assert again.source_id == first.source_id
    sources = repo.list_linked_sources()
    assert len(sources) == 1
    assert (sources[0].title, sources[0].content_hash, sources[0].last_status) == (
        "A2",
        "h2",
        "failed",
    )
    with transaction(conn):
        repo.update_source_check(first.source_id, "changed", "h3")
    stored = repo.get_linked_source(first.source_id)
    assert stored is not None
    assert (stored.content_hash, stored.last_status) == ("h3", "changed")
    assert repo.get_linked_source("ls-missing") is None


def test_check_runs_are_inserted_and_listed_newest_first(
    conn: sqlite3.Connection, repo: UpdateRepository
) -> None:
    older = SourceCheckRun(
        run_id="scr-1",
        started_at="2026-10-01T00:00:00",
        finished_at="2026-10-01T00:00:01",
        checked=2,
        changed=1,
        failed=1,
        errors=[{"sourceId": "ls-1", "error": "X"}],
    )
    newer = older.model_copy(update={"run_id": "scr-2", "started_at": "2026-10-02T00:00:00"})
    with transaction(conn):
        repo.insert_check_run(older)
        repo.insert_check_run(newer)
    assert repo.list_check_runs() == [newer, older]
