"""Models, errors and the up_ schema (plan Step 4; entities.md, US8.1)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from brahma.updates.db import ensure_up_schema, up_connect
from brahma.updates.errors import DraftFailed, SourceFetchError
from brahma.updates.models import DraftedChanges, Proposal, ProposalIn
from brahma.updates.service import target_version

UP_TABLES = {"up_proposal", "up_proposal_change", "up_linked_source", "up_source_check_run"}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {r["name"] for r in rows}


def test_schema_is_created_with_the_platform_tables_and_twice_is_harmless(tmp_db: Path) -> None:
    first = up_connect(tmp_db)
    ensure_up_schema(first)
    first.close()
    second = up_connect(tmp_db)
    try:
        tables = _tables(second)
        assert tables >= UP_TABLES
        assert "pf_audit_entry" in tables
    finally:
        second.close()


def test_drafted_changes_refuse_extra_fields() -> None:
    valid = {"changes": [{"nodeId": "IBD-N36", "content": "Short paraphrase."}], "summary": "s"}
    assert DraftedChanges.model_validate(valid).changes[0].node_id == "IBD-N36"
    with pytest.raises(ValidationError):
        DraftedChanges.model_validate({**valid, "publish": True})
    with pytest.raises(ValidationError):
        DraftedChanges.model_validate(
            {"changes": [{"nodeId": "IBD-N36", "content": "x", "sourceIds": []}], "summary": "s"}
        )


def test_proposal_status_and_origin_are_checked_by_model_and_database(
    conn: sqlite3.Connection,
) -> None:
    base = {
        "proposalId": "pr-1",
        "pack": "IBD",
        "baseVersion": "1.0",
        "targetVersion": "1.1 draft",
        "proposerProfileId": "p-maya",
        "origin": "doctor",
        "changeSet": {"changeSummary": "c"},
        "comment": "c",
        "status": "proposed",
        "createdAt": "2026-10-30T00:00:00+00:00",
    }
    assert Proposal.model_validate(base).status == "proposed"
    with pytest.raises(ValidationError):
        Proposal.model_validate({**base, "status": "live"})
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO up_proposal (proposal_id, pack, base_version, target_version, "
            "proposer_profile_id, origin, change_set_json, comment, status, created_at) "
            "VALUES ('pr-x', 'IBD', '1.0', '1.1 draft', 'p-maya', 'doctor', '{}', 'c', "
            "'live', 'now')"
        )
    with pytest.raises(sqlite3.IntegrityError):  # a decided proposal needs decided_at
        conn.execute(
            "INSERT INTO up_proposal (proposal_id, pack, base_version, target_version, "
            "proposer_profile_id, origin, change_set_json, comment, status, created_at) "
            "VALUES ('pr-y', 'IBD', '1.0', '1.1 draft', 'p-maya', 'doctor', '{}', 'c', "
            "'rejected', 'now')"
        )


def test_proposal_in_requires_a_real_comment_and_a_change() -> None:
    ok = ProposalIn(node_id="IBD-N36", change={"content": "x"}, comment="  why  ")
    assert ok.comment == "why"
    assert ok.pack == "IBD"
    with pytest.raises(ValidationError):
        ProposalIn(node_id="IBD-N36", change={"content": "x"}, comment="   ")
    with pytest.raises(ValidationError):
        ProposalIn(node_id="IBD-N36", change={}, comment="why")


def test_target_version_and_error_labels() -> None:
    assert target_version("1.0") == "1.1 draft"
    assert target_version("2.9") == "2.10 draft"
    assert SourceFetchError("x", refused=True).log_label() == "SourceFetchError refused"
    assert SourceFetchError("x").log_label() == "SourceFetchError failed"
    assert DraftFailed("x", cause_label="ModelTimeout").log_label() == "DraftFailed (ModelTimeout)"
    assert DraftFailed("x").log_label() == "DraftFailed"
