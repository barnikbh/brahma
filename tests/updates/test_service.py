"""UpdateService and the source checker (plan Step 11; US8.1-US8.3, BR1, BR2, BR3, BR4).

Pages are synthetic HTML served through respx; the model is the recorded provider.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from brahma.knowledge import KnowledgeService, NodeNotFound, PackLoadError, PackVersionRef
from brahma.knowledge.db import kg_connect
from brahma.platform.errors import ConfigError, Forbidden, ProfileNotFound
from brahma.platform.identity import IdentityService
from brahma.updates import check
from brahma.updates.errors import (
    CopyFlagged,
    DraftFailed,
    ProposalClosed,
    ProposalInvalid,
    ProposalNotFound,
    SourceFetchError,
)
from brahma.updates.fetch import SafeFetcher
from brahma.updates.models import ProposalIn
from brahma.updates.repository import UpdateRepository
from brahma.updates.service import UpdateService
from tests.updates.conftest import DOCTOR, REVIEWER, SOURCE_URL, SYNTHETIC_PAGE

NEW_N36 = "Crohn's disease of the colon alone, sparing the small bowel (reviewed wording)."
NEW_N37 = "Crohn's disease of both the terminal ileum and the colon (reviewed wording)."
# 30 consecutive words of the first paragraph of SYNTHETIC_PAGE.
COPIED = (
    "This made up page exists only for automated tests of the Brahma update flow and it "
    "describes no real clinical guidance of any kind whatsoever for any patient at all"
)


def _suggest(node_id: str = "IBD-N36", content: str = NEW_N36, **extra: Any) -> ProposalIn:
    return ProposalIn(
        node_id=node_id, change={"content": content}, comment="Clearer wording", **extra
    )


def test_a_proposal_shows_before_and_after_and_links_its_source(
    updates: UpdateService,
    knowledge: KnowledgeService,
    page: Callable[..., respx.Route],
    audit_kinds: Callable[[], list[dict[str, Any]]],
    conn: sqlite3.Connection,
) -> None:
    page()
    old = knowledge.get_node(knowledge.live_version("IBD"), "IBD-N36").content
    section = "Colonic disease in this invented note is described as sparing the small bowel."
    proposal = updates.create_proposal(_suggest(source_url=SOURCE_URL, section=section), DOCTOR)
    assert (proposal.status, proposal.origin, proposal.base_version) == (
        "proposed",
        "doctor",
        "1.1",
    )
    assert proposal.target_version == "1.2 draft"
    change = proposal.changes[0]
    assert change.before is not None
    assert change.before["content"] == old
    assert change.after["content"] == NEW_N36
    assert change.source_passage == section
    assert not change.copy_flag
    assert updates.get_proposal(proposal.proposal_id) == proposal
    source = UpdateRepository(conn).get_linked_source(proposal.source_id or "")
    assert source is not None
    assert (source.url, source.title) == (SOURCE_URL, "Synthetic colitis note")
    assert knowledge.live_version("IBD").number == "1.1"  # nothing live yet
    assert [e["kind"] for e in audit_kinds()] == ["proposal_created"]


def test_a_change_that_copies_the_source_is_flagged_and_cannot_publish(
    updates: UpdateService, page: Callable[..., respx.Route]
) -> None:
    page()
    proposal = updates.create_proposal(_suggest(content=COPIED, source_url=SOURCE_URL), DOCTOR)
    change = proposal.changes[0]
    assert change.copy_flag
    assert change.source_passage is not None
    assert change.source_passage.startswith("This made up page")
    with pytest.raises(CopyFlagged) as caught:
        updates.publish(proposal.proposal_id, REVIEWER)
    assert caught.value.node_ids == ["IBD-N36"]
    assert updates.get_proposal(proposal.proposal_id).status == "proposed"


@pytest.mark.parametrize(
    ("proposal", "error"),
    [
        (ProposalIn(node_id="IBD-N36", change={"type": "drug"}, comment="c"), ProposalInvalid),
        (ProposalIn(node_id="IBD-N36", change={"label": ""}, comment="c"), ProposalInvalid),
        (ProposalIn(node_id="IBD-N36", change={"colour": "red"}, comment="c"), ProposalInvalid),
        (ProposalIn(node_id="IBD-N999", change={"content": "x"}, comment="c"), NodeNotFound),
        (
            ProposalIn(node_id="IBD-N36", change={"sourceIds": ["IBD-S404"]}, comment="c"),
            PackLoadError,
        ),
        (_suggest(source_url="http://127.0.0.1/admin"), SourceFetchError),
    ],
)
def test_an_invalid_proposal_raises_and_stores_nothing(
    updates: UpdateService, proposal: ProposalIn, error: type[Exception]
) -> None:
    with pytest.raises(error):
        updates.create_proposal(proposal, DOCTOR)
    assert updates.list_proposals() == []


def test_unchanged_nodes_and_unknown_profiles_are_refused(updates: UpdateService) -> None:
    with pytest.raises(ProposalInvalid):
        updates.create_proposal(
            _suggest(content="Crohn's disease affecting the colon only."), DOCTOR
        )
    with pytest.raises(ProfileNotFound):
        updates.create_proposal(_suggest(), "p-nobody")
    with pytest.raises(ProposalNotFound):
        updates.get_proposal("pr-missing")


def test_only_the_reviewer_may_publish_or_reject(updates: UpdateService) -> None:
    proposal = updates.create_proposal(_suggest(), DOCTOR)
    with pytest.raises(Forbidden):
        updates.publish(proposal.proposal_id, DOCTOR)
    with pytest.raises(Forbidden):
        updates.reject(proposal.proposal_id, DOCTOR, "no")
    assert updates.get_proposal(proposal.proposal_id).status == "proposed"


def test_publishing_bumps_the_version_for_new_sessions_and_keeps_the_old_one(
    updates: UpdateService,
    knowledge: KnowledgeService,
    tmp_db: Path,
    audit_kinds: Callable[[], list[dict[str, Any]]],
) -> None:
    proposal = updates.create_proposal(_suggest(), DOCTOR)
    published = updates.publish(proposal.proposal_id, REVIEWER, "Checked against the source")
    assert (published.status, published.published_version) == ("published", "1.2")
    assert published.reviewer_profile_id == REVIEWER
    fresh = KnowledgeService(kg_connect(tmp_db))  # a new session opens the database again
    try:
        live = fresh.live_version("IBD")
        assert live.number == "1.2"
        assert fresh.get_node(live, "IBD-N36").content == NEW_N36
        versions = {v.number: v.status for v in fresh.list_versions("IBD")}
        assert versions == {"1.2": "live", "1.1": "superseded"}
        old = fresh.get_node(PackVersionRef(pack="IBD", number="1.1"), "IBD-N36")
        assert old.content != NEW_N36
        assert knowledge.live_version("IBD").number == "1.2"
    finally:
        fresh.close()
    row = audit_kinds()[-1]
    assert (row["kind"], row["profileId"], row["packVersion"]) == (
        "proposal_published",
        REVIEWER,
        "IBD 1.2",
    )
    assert (row["publishedVersion"], row["rebased"]) == ("1.2", False)
    with pytest.raises(ProposalClosed):
        updates.publish(proposal.proposal_id, REVIEWER)


def test_a_proposal_on_an_older_base_is_reapplied_to_the_live_version(
    updates: UpdateService,
    knowledge: KnowledgeService,
    audit_kinds: Callable[[], list[dict[str, Any]]],
) -> None:
    first = updates.create_proposal(_suggest("IBD-N36", NEW_N36), DOCTOR)
    second = updates.create_proposal(_suggest("IBD-N37", NEW_N37), DOCTOR)
    updates.publish(first.proposal_id, REVIEWER)
    result = updates.publish(second.proposal_id, REVIEWER)
    assert (result.base_version, result.published_version) == ("1.1", "1.3")
    live = knowledge.live_version("IBD")
    assert knowledge.get_node(live, "IBD-N36").content == NEW_N36
    assert knowledge.get_node(live, "IBD-N37").content == NEW_N37
    assert audit_kinds()[-1]["rebased"] is True


def test_a_change_that_no_longer_validates_stays_proposed(
    updates: UpdateService,
    knowledge: KnowledgeService,
    monkeypatch: pytest.MonkeyPatch,
    audit_kinds: Callable[[], list[dict[str, Any]]],
) -> None:
    proposal = updates.create_proposal(_suggest(), DOCTOR)

    def refuse(*_args: Any) -> Any:
        raise PackLoadError("IBD-N36", "edge target missing")

    monkeypatch.setattr(knowledge, "create_version", refuse)
    with pytest.raises(PackLoadError):
        updates.publish(proposal.proposal_id, REVIEWER)
    assert updates.get_proposal(proposal.proposal_id).status == "proposed"
    assert [e["kind"] for e in audit_kinds()] == ["proposal_created"]


def test_rejecting_needs_a_comment_and_is_audited(
    updates: UpdateService, audit_kinds: Callable[[], list[dict[str, Any]]]
) -> None:
    proposal = updates.create_proposal(_suggest(), DOCTOR)
    with pytest.raises(ProposalInvalid):
        updates.reject(proposal.proposal_id, REVIEWER, "   ")
    rejected = updates.reject(proposal.proposal_id, REVIEWER, "Not supported by the source")
    assert (rejected.status, rejected.review_comment) == ("rejected", "Not supported by the source")
    assert audit_kinds()[-1] == {
        "kind": "proposal_rejected",
        "profileId": REVIEWER,
        "packVersion": "IBD 1.1",
        "proposalId": proposal.proposal_id,
        "comment": "Not supported by the source",
    }
    with pytest.raises(ProposalClosed):
        updates.publish(proposal.proposal_id, REVIEWER)


def test_history_merges_live_superseded_proposed_and_rejected(updates: UpdateService) -> None:
    published = updates.create_proposal(_suggest("IBD-N36", NEW_N36), DOCTOR)
    updates.publish(published.proposal_id, REVIEWER, "Looks right")
    rejected = updates.create_proposal(_suggest("IBD-N37", NEW_N37), DOCTOR)
    updates.reject(rejected.proposal_id, REVIEWER, "No")
    pending = updates.create_proposal(_suggest("IBD-N37", NEW_N37), DOCTOR)
    history = updates.version_history("IBD")
    by_status = {e.status: e for e in history}
    assert set(by_status) == {"live", "superseded", "proposed", "rejected"}
    assert (by_status["live"].version, by_status["live"].comment) == ("1.2", "Looks right")
    assert by_status["live"].proposal_id == published.proposal_id
    assert by_status["live"].author == REVIEWER
    assert by_status["proposed"].proposal_id == pending.proposal_id
    assert by_status["proposed"].version == "1.3 draft"
    assert by_status["rejected"].comment == "No"
    assert [e.date for e in history] == sorted((e.date for e in history), reverse=True)


def test_drafting_from_a_source_stores_a_drafted_proposal(
    updates: UpdateService, page: Callable[..., respx.Route]
) -> None:
    page()
    proposal = updates.draft_from_source("IBD", SOURCE_URL, DOCTOR)
    assert proposal.origin == "drafted"
    assert [c.node_id for c in proposal.changes] == ["IBD-N36"]
    change = proposal.changes[0]
    assert change.after["content"].startswith("Crohn's disease limited to the colon")
    assert change.source_passage is not None
    assert "small bowel" in change.source_passage
    assert not change.copy_flag
    assert proposal.comment.startswith("Clarify")


def test_a_failed_or_empty_draft_stores_nothing(
    make_service: Callable[..., UpdateService],
    conn: sqlite3.Connection,
    knowledge: KnowledgeService,
    identity: IdentityService,
    fetcher: SafeFetcher,
    page: Callable[..., respx.Route],
    write_draft: Callable[[dict[str, Any]], Path],
    tmp_path: Path,
) -> None:
    page()
    failing = make_service(tmp_path / "no-fixtures")
    with pytest.raises(DraftFailed):
        failing.draft_from_source("IBD", SOURCE_URL, DOCTOR)
    empty = make_service(write_draft({"changes": [], "summary": "Nothing to change"}))
    with pytest.raises(DraftFailed) as nothing:
        empty.draft_from_source("IBD", SOURCE_URL, DOCTOR)
    assert "no changes" in nothing.value.reason

    def no_config() -> Any:
        raise ConfigError("BRAHMA_MODEL_PROVIDER is not set")

    for gateway in (None, no_config):
        unconfigured = UpdateService(conn, knowledge, identity, fetcher=fetcher, gateway=gateway)
        with pytest.raises(DraftFailed):
            unconfigured.draft_from_source("IBD", SOURCE_URL, DOCTOR)
    assert failing.list_proposals() == []


def test_check_sources_drafts_on_change_skips_failures_and_records_the_run(
    updates: UpdateService,
    conn: sqlite3.Connection,
    http: respx.MockRouter,
    page: Callable[..., respx.Route],
    caplog: pytest.LogCaptureFixture,
) -> None:
    page()
    updates.create_proposal(_suggest(source_url=SOURCE_URL), DOCTOR)
    gone = "https://gone.example.org/page"
    page(gone)
    updates.create_proposal(_suggest("IBD-N37", NEW_N37, source_url=gone), DOCTOR)

    unchanged = updates.check_sources()
    assert (unchanged.checked, unchanged.changed, unchanged.failed) == (2, 0, 0)

    page(html=SYNTHETIC_PAGE.replace("sparing", "not involving"))
    http.get(gone).mock(return_value=httpx.Response(503))
    with caplog.at_level("WARNING", logger="brahma.updates"):
        run = updates.check_sources()
    assert (run.checked, run.changed, run.failed) == (2, 1, 1)
    assert run.errors[0]["error"] == "SourceFetchError failed"
    assert gone not in caplog.text  # only the source ID and the error class are logged
    scheduled = updates.list_proposals(status="proposed")[0]
    assert scheduled.origin == "scheduled"
    statuses = {s.url: s.last_status for s in UpdateRepository(conn).list_linked_sources()}
    assert statuses == {SOURCE_URL: "changed", gone: "failed"}
    assert [r.run_id for r in UpdateRepository(conn).list_check_runs()] == [
        run.run_id,
        unchanged.run_id,
    ]


def test_check_interval_scheduler_and_cli(
    updates: UpdateService, tmp_db: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check.check_interval_hours({}) == 24.0
    assert check.check_interval_hours({check.ENV_HOURS: "0"}) == 0.0
    assert check.check_interval_hours({check.ENV_HOURS: " 6 "}) == 6.0
    for bad in ("soon", "-1", "1000"):
        with pytest.raises(ValueError, match=check.ENV_HOURS):
            check.check_interval_hours({check.ENV_HOURS: bad})
    assert check.SourceCheckScheduler.from_env(updates, {check.ENV_HOURS: "0"}) is None
    assert check.SourceCheckScheduler.from_env(updates, {}) is not None
    with pytest.raises(ValueError):
        check.SourceCheckScheduler(updates, 0)

    scheduler = check.SourceCheckScheduler(updates, interval_s=0.01)
    scheduler.start()
    deadline = time.monotonic() + 5
    while not scheduler.runs and time.monotonic() < deadline:
        time.sleep(0.01)
    scheduler.stop()
    assert scheduler.runs and scheduler.runs[0].checked == 0

    assert check.main([]) == 0
    assert json.loads(capsys.readouterr().out)["checked"] == 0


def test_the_cli_refuses_a_bad_interval(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(check.ENV_HOURS, "weekly")
    assert check.main([]) == 2
    assert check.ENV_HOURS in capsys.readouterr().err
