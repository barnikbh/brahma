"""Repositories: seeding, history filters, rollback and audit timings (BR1.3, BR2.1, NFR1.2)."""

from __future__ import annotations

import sqlite3
import time

import pytest

from brahma.platform.audit.models import SessionFilter
from brahma.platform.audit.repository import AuditRepository
from brahma.platform.db import transaction
from brahma.platform.identity.repository import DisclaimerRepository
from brahma.platform.profiles import ProfileRepository
from tests.platform.factories import make_entry, make_session


@pytest.fixture
def seeded(conn: sqlite3.Connection) -> sqlite3.Connection:
    ProfileRepository(conn).seed()
    return conn


def test_seeding_twice_adds_no_duplicates(conn: sqlite3.Connection) -> None:
    profiles = ProfileRepository(conn)
    profiles.seed()
    profiles.seed()

    assert conn.execute("SELECT COUNT(*) FROM pf_profile").fetchone()[0] == 4
    assert [p.profile_id for p in profiles.list()] == ["p-maya", "p-reviewer", "p-urologist"]
    benchmark = profiles.get("p-benchmark")
    assert benchmark is not None and benchmark.role == "system" and not benchmark.listed
    assert profiles.get("p-nobody") is None


def test_history_filters_by_outcome_and_text(seeded: sqlite3.Connection) -> None:
    repo = AuditRepository(seeded)
    with transaction(seeded):
        answered = repo.add_session(make_session())
        needs = repo.add_session(
            make_session(
                outcome="needs_data",
                inputs={"text": "Blood in urine, no imaging", "findings": [{"name": "Haematuria"}]},
                answer={"summary": "Imaging needed", "sections": [], "counts": {}},
            )
        )

    by_outcome = repo.list_sessions(SessionFilter(outcome="needs_data"))
    assert [s.session_id for s in by_outcome] == [needs]
    assert [s.session_id for s in repo.list_sessions(SessionFilter(text="HAEMATURIA"))] == [needs]
    by_answer_label = repo.list_sessions(SessionFilter(text="ulcerative"))
    assert [s.session_id for s in by_answer_label] == [answered]
    assert [s.session_id for s in repo.list_sessions(SessionFilter(text=answered))] == [answered]
    assert repo.list_sessions(SessionFilter(text="50%")) == []


def test_history_is_newest_first_with_labels(seeded: sqlite3.Connection) -> None:
    repo = AuditRepository(seeded)
    with transaction(seeded):
        first = repo.add_session(make_session(caseId="case-a"))
        second = repo.add_session(make_session(caseId="case-b"))

    summaries = repo.list_sessions(SessionFilter())
    assert [s.session_id for s in summaries] == [second, first]
    assert summaries[0].label.startswith("Bloody diarrhoea")
    assert summaries[0].pack_version == "IBD 1.3"


def test_benchmark_sessions_hidden_by_default_and_shown_on_request(
    seeded: sqlite3.Connection,
) -> None:
    repo = AuditRepository(seeded)
    with transaction(seeded):
        clinic = repo.add_session(make_session())
        bench = repo.add_session(make_session(benchmarkRunId="run-1", profileId="p-benchmark"))
        repo.add_session(make_session(benchmarkRunId="run-2", profileId="p-benchmark"))

    assert [s.session_id for s in repo.list_sessions(SessionFilter())] == [clinic]
    assert len(repo.list_sessions(SessionFilter(include_benchmark=True))) == 3
    only_run = repo.list_sessions(SessionFilter(benchmark_run_id="run-1"))
    assert [s.session_id for s in only_run] == [bench]


def test_failure_mid_transaction_rolls_back(seeded: sqlite3.Connection) -> None:
    repo = AuditRepository(seeded)
    kept = repo.append(make_entry())

    with pytest.raises(sqlite3.IntegrityError), transaction(seeded):
        repo.add_entry(make_entry(kind="patient_updated"))
        repo.add_entry(make_entry(profileId="p-unknown"))  # foreign key fails

    rows = seeded.execute("SELECT entry_id FROM pf_audit_entry").fetchall()
    assert [r["entry_id"] for r in rows] == [kept]


def test_get_session_and_entries_round_trip(seeded: sqlite3.Connection) -> None:
    repo = AuditRepository(seeded)
    with transaction(seeded):
        session_id = repo.add_session(make_session())
        repo.add_entry(make_entry(kind="session_recorded", sessionId=session_id))

    record = repo.get_session(session_id)
    assert record is not None
    assert record.inputs.findings[0]["unit"] == "µg/g"
    assert [e.kind for e in repo.entries_for_session(session_id)] == ["session_recorded"]
    assert repo.get_session("s-missing") is None


def test_disclaimer_repository_stores_acceptances(seeded: sqlite3.Connection) -> None:
    repo = DisclaimerRepository(seeded)
    with transaction(seeded):
        acceptance_id = repo.add("p-maya", "1", "IBD 1.3")

    stored = repo.list_for("p-maya", "1")
    assert [(a.acceptance_id, a.pack_version) for a in stored] == [(acceptance_id, "IBD 1.3")]
    assert repo.list_for("p-maya", "2") == []


@pytest.mark.timing
def test_append_and_record_are_under_50_ms(seeded: sqlite3.Connection) -> None:
    repo = AuditRepository(seeded)
    started = time.perf_counter()
    repo.append(make_entry())
    append_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    with transaction(seeded):
        session_id = repo.add_session(make_session())
        repo.add_entry(make_entry(kind="session_recorded", sessionId=session_id))
    record_ms = (time.perf_counter() - started) * 1000

    assert append_ms < 50
    assert record_ms < 50


@pytest.mark.timing
def test_listing_1000_sessions_is_under_200_ms(seeded: sqlite3.Connection) -> None:
    repo = AuditRepository(seeded)
    with transaction(seeded):
        for i in range(1000):
            repo.add_session(make_session(caseId=f"case-{i:04d}"))

    started = time.perf_counter()
    summaries = repo.list_sessions(SessionFilter(text="calprotectin"))
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert len(summaries) == 1000
    assert elapsed_ms < 200
