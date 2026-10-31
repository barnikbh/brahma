"""CaseService (plan step 10, C5): cases, versions, patient audit, edits and forms."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from brahma.cases import (
    Case,
    CaseNotFound,
    CaseService,
    DoseResult,
    FormAlreadySubmitted,
    InvalidCase,
    InvalidPatientChange,
    InvalidTreatmentEdit,
    MessageIn,
    MessageNotFound,
    NewPatient,
    NotADrugNode,
)
from brahma.knowledge import ChangeSet, KnowledgeService, PackVersionRef, VersionNotFound
from brahma.platform.audit.repository import AuditRepository
from brahma.platform.errors import AuditInvalid
from tests.cases.conftest import IBD_PACK, OWNER

AuditReader = Callable[[str], list[dict[str, Any]]]
IBD_LIVE = PackVersionRef(pack="IBD", number="1.1")


def test_create_case_is_synthetic_and_audited(
    cases: CaseService, demo_patient: NewPatient, demo_case: Case, audit_entries: AuditReader
) -> None:
    assert re.fullmatch(r"BR-[0-9A-F]{6}", demo_case.case_id)
    assert demo_case.synthetic is True
    assert (demo_case.origin, demo_case.status) == ("clinic", "new")
    assert cases.get_case(demo_case.case_id) == demo_case
    assert cases.get_patient(demo_case.case_id).allergies == ["penicillin"]
    assert [e["kind"] for e in audit_entries(demo_case.case_id)] == ["case_created"]
    with pytest.raises(InvalidCase):
        cases.create_case(demo_patient, OWNER, origin="benchmark")
    with pytest.raises(InvalidCase):
        cases.create_case(demo_patient, OWNER, benchmark_run_id="run-1")
    with pytest.raises(AuditInvalid):
        cases.create_case(demo_patient, "p-nobody")
    with pytest.raises(CaseNotFound):
        cases.get_case("BR-NOPE00")


def test_newer_version_after_a_new_version_is_published(
    cases: CaseService, demo_case: Case, knowledge: KnowledgeService
) -> None:
    case_id = demo_case.case_id
    assert cases.newer_version(case_id) is None
    cases.pin(case_id, IBD_LIVE)
    assert cases.newer_version(case_id) is None

    knowledge.create_version("IBD", IBD_LIVE, ChangeSet(change_summary="Wording fix"), OWNER)

    assert cases.newer_version(case_id) == PackVersionRef(pack="IBD", number="1.2")
    assert cases.get_case(case_id).pinned_pack_version == IBD_LIVE
    with pytest.raises(VersionNotFound):
        cases.pin(case_id, PackVersionRef(pack="IBD", number="9.0"))


def test_update_patient_writes_its_audit_entry(
    cases: CaseService, demo_case: Case, audit_entries: AuditReader
) -> None:
    updated = cases.update_patient(demo_case.case_id, {"weightKg": 62}, OWNER)

    assert updated.weight_kg == 62
    assert cases.get_patient(demo_case.case_id).weight_kg == 62
    entry = audit_entries(demo_case.case_id)[-1]
    assert entry["kind"] == "patient_updated"
    assert entry["profileId"] == OWNER
    assert entry["fields"] == ["weightKg"]
    assert (entry["before"], entry["after"]) == ({"weightKg": 58.0}, {"weightKg": 62.0})
    dose = cases.compute_dose(demo_case.case_id, "IBD-N53")
    assert isinstance(dose, DoseResult)
    assert dose.value == 310


@pytest.mark.parametrize(
    "changes",
    [{"syntheticName": "x"}, {"weightKg": 500}, {"sex": None}, {}, {"age": "old"}],
)
def test_invalid_patient_change_is_refused_and_not_audited(
    cases: CaseService, demo_case: Case, audit_entries: AuditReader, changes: dict[str, Any]
) -> None:
    with pytest.raises(InvalidPatientChange):
        cases.update_patient(demo_case.case_id, changes, OWNER)

    assert cases.get_patient(demo_case.case_id).weight_kg == 58
    assert [e["kind"] for e in audit_entries(demo_case.case_id)] == ["case_created"]


def test_audit_failure_rolls_back_the_patient_change(
    cases: CaseService,
    demo_case: Case,
    audit_entries: AuditReader,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def failing_add_entry(self: AuditRepository, entry: object) -> str:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(AuditRepository, "add_entry", failing_add_entry)

    with pytest.raises(sqlite3.OperationalError):
        cases.update_patient(demo_case.case_id, {"weightKg": 62}, OWNER)

    monkeypatch.undo()
    assert cases.get_patient(demo_case.case_id).weight_kg == 58
    assert [e["kind"] for e in audit_entries(demo_case.case_id)] == ["case_created"]
    assert '"error": "OperationalError"' in caplog.text
    assert "62" not in caplog.text


def test_apply_edit_records_the_original_and_reruns_the_checks(
    cases: CaseService, demo_case: Case, audit_entries: AuditReader
) -> None:
    outcome = cases.apply_edit(demo_case.case_id, "IBD-N53", {"dose_value": 10}, OWNER)

    assert outcome.edit.original["doseValue"] == 5
    assert outcome.edit.new_values["doseValue"] == 10
    assert outcome.edit.new_values["drugNodeId"] == "IBD-N53"
    assert isinstance(outcome.dose, DoseResult)
    assert outcome.dose.formula == "10 mg/kg × 58 kg = 580 mg"
    assert [r.check for r in outcome.safety] == [
        "allergy",
        "pregnancy",
        "interaction",
        "duplicate_class",
    ]
    entry = audit_entries(demo_case.case_id)[-1]
    assert entry["kind"] == "treatment_edit"
    assert (entry["nodeId"], entry["editId"]) == ("IBD-N53", outcome.edit.edit_id)
    assert entry["original"]["doseValue"] == 5
    again = cases.compute_dose(demo_case.case_id, "IBD-N53")
    assert isinstance(again, DoseResult)
    assert again.value == 580


def test_changing_the_drug_resets_to_the_new_drugs_values(
    cases: CaseService, demo_case: Case
) -> None:
    outcome = cases.apply_edit(
        demo_case.case_id, "IBD-N53", {"drug": "Mesalazine", "doseValue": 99}, OWNER
    )

    values = outcome.edit.new_values
    assert values["drugNodeId"] == "IBD-N50"
    assert (values["drug"], values["route"], values["doseValue"]) == ("mesalamine", "oral", 2)
    assert values["frequency"] == "once daily"
    assert isinstance(outcome.dose, DoseResult)
    assert (outcome.dose.value, outcome.dose.unit, outcome.dose.node_ids) == (2, "g", ["IBD-N50"])
    assert all(r.drug_node_id == "IBD-N53" for r in outcome.safety)
    for bad in ({"colour": "red"}, {"drug": "unknownmab"}, {"doseValue": "lots"}, {}):
        with pytest.raises(InvalidTreatmentEdit):
            cases.apply_edit(demo_case.case_id, "IBD-N53", bad, OWNER)
    with pytest.raises(NotADrugNode):
        cases.apply_edit(demo_case.case_id, "IBD-N3", {"route": "oral"}, OWNER)


def test_a_form_cannot_be_submitted_twice(cases: CaseService, demo_case: Case) -> None:
    case_id = demo_case.case_id
    form_id = cases.append_message(
        case_id, MessageIn(author="brahma", kind="form", form_kind="weight")
    )
    text_id = cases.append_message(case_id, MessageIn(author="doctor", kind="text"))
    cases.submit_form(case_id, form_id)

    with pytest.raises(FormAlreadySubmitted):
        cases.submit_form(case_id, form_id)
    with pytest.raises(FormAlreadySubmitted):
        cases.save_form_draft(case_id, form_id, {"weightKg": 60})
    with pytest.raises(FormAlreadySubmitted):
        cases.submit_form(case_id, text_id)
    with pytest.raises(MessageNotFound):
        cases.submit_form(case_id, "msg-missing")
    assert [m.message_id for m in cases.list_messages(case_id)] == [form_id, text_id]


def test_set_status_and_open_close(
    cases: CaseService, demo_case: Case, demo_patient: NewPatient, tmp_path: Path
) -> None:
    cases.set_status(demo_case.case_id, "answered")
    assert cases.get_case(demo_case.case_id).status == "answered"
    with pytest.raises(InvalidCase):
        cases.set_status(demo_case.case_id, "closed")  # type: ignore[arg-type]

    path = tmp_path / "other.db"
    opened = CaseService.open(path)
    try:
        with pytest.raises(VersionNotFound):
            opened.set_findings(opened.create_case(demo_patient, OWNER).case_id, [])
        opened._knowledge.load_pack(IBD_PACK)
        case = opened.create_case(demo_patient, OWNER)
        assert opened.set_findings(case.case_id, []) == []
    finally:
        opened.close()
