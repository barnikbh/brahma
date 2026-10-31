"""Dose and safety (plan step 10, BR4.1-BR4.3): formulas and grounded checks."""

from __future__ import annotations

import pytest

from brahma.cases import (
    NOT_CHECKED_MESSAGE,
    Case,
    CaseService,
    DoseResult,
    MissingWeight,
    NewPatient,
    NotADrugNode,
    Patient,
    SafetyResult,
)
from brahma.cases.catalog import NodeCatalog
from brahma.cases.safety import EffectiveDrug, compute_dose, safety_checks
from brahma.knowledge import NodeNotFound
from brahma.knowledge.models import DrugFields
from tests.cases.conftest import OWNER


def _by_check(results: list[SafetyResult], drug: str) -> dict[str, SafetyResult]:
    return {r.check: r for r in results if r.drug_node_id == drug}


def _drug(**overrides: object) -> EffectiveDrug:
    fields = {
        "drug": "testdrug",
        "synonyms": [],
        "drugClass": "test class",
        "route": "oral",
        "doseValue": 10,
        "doseUnit": "mg",
        "doseBasis": "absolute",
        "rounding": "not applicable",
        "frequency": "daily",
        "duration": "a week",
        "contraindications": ["pregnancy"],
        **overrides,
    }
    return EffectiveDrug("X-N1", "X-N1", DrugFields.model_validate(fields))


def test_per_kg_dose_for_58_kg_shows_its_formula(cases: CaseService, demo_case: Case) -> None:
    dose = cases.compute_dose(demo_case.case_id, "IBD-N53")

    assert isinstance(dose, DoseResult)
    assert (dose.value, dose.unit) == (290, "mg")
    assert dose.formula == "5 mg/kg × 58 kg = 290 mg"
    assert dose.node_ids == ["IBD-N53"]


def test_absolute_dose_and_rounding_rule(
    cases: CaseService, demo_case: Case, safety_cases: CaseService, demo_patient: NewPatient
) -> None:
    absolute = cases.compute_dose(demo_case.case_id, "IBD-N50")
    tsf_case = safety_cases.create_case(demo_patient, OWNER)
    rounded = safety_cases.compute_dose(tsf_case.case_id, "TSF-N3")

    assert isinstance(absolute, DoseResult)
    assert (absolute.value, absolute.unit, absolute.formula) == (2, "g", "2 g (fixed dose)")
    assert isinstance(rounded, DoseResult)
    assert rounded.value == 150
    assert rounded.formula == "2.5 mg/kg × 58 kg = 145 mg, rounded to 150 mg"


def test_no_weight_returns_missing_weight_and_non_drug_is_refused(
    cases: CaseService, demo_patient: NewPatient
) -> None:
    case = cases.create_case(demo_patient.model_copy(update={"weight_kg": None}), OWNER)

    result = cases.compute_dose(case.case_id, "IBD-N53")

    assert isinstance(result, MissingWeight)
    assert result.node_id == "IBD-N53"
    with pytest.raises(NotADrugNode):
        cases.compute_dose(case.case_id, "IBD-N3")
    with pytest.raises(NodeNotFound):
        cases.compute_dose(case.case_id, "IBD-N9999")


def test_penicillin_allergy_conflicts_with_a_penicillin_class_drug(
    safety_cases: CaseService, demo_patient: NewPatient
) -> None:
    case = safety_cases.create_case(demo_patient, OWNER)

    checks = _by_check(safety_cases.safety_checks(case.case_id, ["TSF-N2"]), "TSF-N2")

    assert checks["allergy"].status == "conflict"
    assert checks["allergy"].node_ids == ["TSF-N4", "TSF-N2"]


def test_drug_with_no_safety_node_is_not_checked_for_every_check(
    safety_cases: CaseService, demo_patient: NewPatient
) -> None:
    patient = demo_patient.model_copy(
        update={"allergies": ["sulfonamide"], "pregnancy_status": None}
    )
    case = safety_cases.create_case(patient, OWNER)

    results = safety_cases.safety_checks(case.case_id, ["TSF-N3"])

    assert [r.check for r in results] == ["allergy", "pregnancy", "interaction", "duplicate_class"]
    assert all(r.status == "not_checked" for r in results)
    assert all(r.message == NOT_CHECKED_MESSAGE and r.node_ids == [] for r in results)


def test_duplicate_class_conflicts_and_demo_drug_checks_cite_nodes(
    cases: CaseService, demo_case: Case
) -> None:
    results = cases.safety_checks(demo_case.case_id, ["IBD-N51", "IBD-N52", "IBD-N53"])

    duplicate = _by_check(results, "IBD-N51")["duplicate_class"]
    infliximab = _by_check(results, "IBD-N53")
    assert duplicate.status == "conflict"
    assert duplicate.node_ids == ["IBD-N51", "IBD-N52"]
    assert infliximab["duplicate_class"].status == "ok"
    assert infliximab["duplicate_class"].node_ids == ["IBD-N53", "IBD-N51", "IBD-N52", "IBD-N56"]
    assert infliximab["allergy"].status == "ok"
    assert infliximab["allergy"].node_ids == ["IBD-N101"]
    assert infliximab["pregnancy"].status == "ok"
    assert infliximab["interaction"].status == "not_checked"
    assert all(r.status == "not_checked" or r.node_ids for r in results)


def test_interaction_ok_then_conflict_with_a_current_medication(
    cases: CaseService, demo_patient: NewPatient
) -> None:
    plain = cases.create_case(demo_patient.model_copy(update={"current_medication": []}), OWNER)
    on_calcium = cases.create_case(
        demo_patient.model_copy(update={"current_medication": ["Calcium or iron salts "]}), OWNER
    )

    ok = _by_check(cases.safety_checks(plain.case_id, ["IBD-N56"]), "IBD-N56")["interaction"]
    clash = _by_check(cases.safety_checks(on_calcium.case_id, ["IBD-N56"]), "IBD-N56")

    assert (ok.status, ok.node_ids) == ("ok", ["IBD-N100"])
    assert (clash["interaction"].status, clash["interaction"].node_ids) == (
        "conflict",
        ["IBD-N100"],
    )
    assert clash["duplicate_class"].status == "not_checked"


def test_pregnancy_check_is_grounded_in_the_drug_contraindications() -> None:
    catalog = NodeCatalog([])
    base = {
        "patient_id": "pt-1",
        "synthetic_name": "Synthetic B",
        "age": 30,
        "sex": "female",
        "weight_kg": 60,
    }
    pregnant = Patient.model_validate({**base, "pregnancy_status": " Pregnant "})
    unknown = Patient.model_validate(base)

    contraindicated = safety_checks([_drug()], pregnant, catalog)[1]
    unlisted = safety_checks([_drug(contraindications=[])], pregnant, catalog)[1]
    not_recorded = safety_checks([_drug()], unknown, catalog)[1]

    assert (contraindicated.status, contraindicated.node_ids) == ("conflict", ["X-N1"])
    assert unlisted.status == "not_checked"
    assert not_recorded.status == "not_checked"
    assert compute_dose(_drug(doseBasis="per_kg", doseUnit="ug/kg"), 60).formula == (
        "10 ug/kg × 60 kg = 600 ug"
    )
