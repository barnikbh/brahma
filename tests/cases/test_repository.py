"""Repository and lock (plan step 6): search, tab lock, drafts and latest edits."""

from __future__ import annotations

import sqlite3

import pytest

from brahma.cases import Case, CaseService, FindingIn, MessageIn, NewPatient, TreatmentEdit
from brahma.cases.repository import CaseRepository
from tests.cases.conftest import OTHER_OWNER, OWNER, FakeClock


def _calprotectin(cases: CaseService, case: Case) -> None:
    cases.set_findings(
        case.case_id, [FindingIn(kind="finding", name="calprotectin", value=850, unit="ug/g")]
    )


def test_search_finds_by_finding_and_excludes_benchmark_and_other_owners(
    cases: CaseService, demo_patient: NewPatient, demo_case: Case
) -> None:
    benchmark = cases.create_case(demo_patient, OWNER, "benchmark", "run-1")
    other = cases.create_case(demo_patient, OTHER_OWNER)
    for case in (demo_case, benchmark, other):
        _calprotectin(cases, case)

    found = cases.search_patients("Calprotectin", OWNER)

    assert [s.case_id for s in found] == [demo_case.case_id]
    assert found[0].synthetic_name == demo_patient.synthetic_name


def test_search_by_case_id_and_pathway_label_most_recent_first(
    cases: CaseService, demo_patient: NewPatient, demo_case: Case
) -> None:
    second = cases.create_case(demo_patient, OWNER)
    cases.append_message(
        demo_case.case_id,
        MessageIn(author="brahma", kind="pathway", body={"diagnosis": "Ulcerative colitis"}),
    )
    cases.append_message(
        second.case_id,
        MessageIn(author="brahma", kind="pathway", body={"diagnosis": "Ulcerative colitis"}),
    )
    cases.append_message(
        demo_case.case_id, MessageIn(author="doctor", kind="text", body={"text": "crohn"})
    )

    by_label = cases.search_patients("ulcerative", OWNER)
    by_id = cases.search_patients(second.case_id.lower(), OWNER)
    text_only = cases.search_patients("crohn", OWNER)

    assert [s.case_id for s in by_label] == [demo_case.case_id, second.case_id]
    assert [s.case_id for s in by_id] == [second.case_id]
    assert text_only == []


@pytest.mark.parametrize("query", ["no such thing", "%", "_"])
def test_search_with_no_match_returns_empty_list(
    cases: CaseService, demo_case: Case, query: str
) -> None:
    _calprotectin(cases, demo_case)
    assert cases.search_patients(query, OWNER) == []


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_search_lists_the_owners_recent_cases(
    cases: CaseService, demo_case: Case, query: str
) -> None:
    assert [c.case_id for c in cases.search_patients(query, OWNER)] == [demo_case.case_id]
    assert cases.search_patients(query, "p-someone-else") == []


def test_lock_same_tab_held_second_tab_read_only_until_expiry(
    cases: CaseService, demo_case: Case, clock: FakeClock
) -> None:
    case_id = demo_case.case_id

    assert cases.acquire_lock(case_id, "tab-a") == "held"
    assert cases.acquire_lock(case_id, "tab-a") == "held"
    assert cases.acquire_lock(case_id, "tab-b") == "read_only"
    clock.advance(45)
    assert cases.acquire_lock(case_id, "tab-b") == "read_only"
    clock.advance(1)
    assert cases.acquire_lock(case_id, "tab-b") == "held"
    assert cases.acquire_lock(case_id, "tab-a") == "read_only"


def test_release_by_a_tab_without_the_lock_is_a_no_op(
    cases: CaseService, demo_case: Case, conn: sqlite3.Connection
) -> None:
    repo = CaseRepository(conn)
    case_id = demo_case.case_id
    cases.acquire_lock(case_id, "tab-a")

    cases.release_lock(case_id, "tab-b")
    assert repo.lock_holder(case_id) == "tab-a"
    cases.release_lock(case_id, "tab-a")
    assert repo.lock_holder(case_id) is None
    assert cases.acquire_lock(case_id, "tab-b") == "held"


def test_form_draft_saved_then_deleted_on_submit(cases: CaseService, demo_case: Case) -> None:
    case_id = demo_case.case_id
    form_id = cases.append_message(
        case_id, MessageIn(author="brahma", kind="form", form_kind="weight", body={"ask": "kg"})
    )

    cases.save_form_draft(case_id, form_id, {"weightKg": 6})
    cases.save_form_draft(case_id, form_id, {"weightKg": 62})
    assert cases.get_form_drafts(case_id) == {form_id: {"weightKg": 62}}

    cases.submit_form(case_id, form_id)

    assert cases.get_form_drafts(case_id) == {}
    form = next(m for m in cases.list_messages(case_id) if m.message_id == form_id)
    assert form.form_state == "submitted"


def test_latest_edit_per_case_and_node(conn: sqlite3.Connection, demo_case: Case) -> None:
    repo = CaseRepository(conn)

    def edit(edit_id: str, created_at: str, dose: int) -> TreatmentEdit:
        return TreatmentEdit(
            edit_id=edit_id,
            case_id=demo_case.case_id,
            node_id="IBD-N53",
            original={},
            new_values={"doseValue": dose},
            editor_profile_id=OWNER,
            created_at=created_at,
        )

    repo.insert_edit(edit("te-1", "2026-10-30T10:00:00.000001+00:00", 5))
    repo.insert_edit(edit("te-2", "2026-10-30T10:00:00.000002+00:00", 10))

    latest = repo.latest_edit(demo_case.case_id, "IBD-N53")
    assert latest is not None
    assert latest.edit_id == "te-2"
    assert repo.latest_edit(demo_case.case_id, "IBD-N50") is None
