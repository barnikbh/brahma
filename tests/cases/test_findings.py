"""Findings (plan step 10, BR2): conversion, invalid, confirm_range, conflict, readiness."""

from __future__ import annotations

from brahma.cases import Case, CaseService, FindingIn, NewPatient
from tests.cases.conftest import OWNER


def _hb(value: float | str | None, unit: str | None = "g/L") -> FindingIn:
    return FindingIn(kind="finding", name="Hb", value=value, unit=unit)


def test_hb_in_g_per_l_is_converted_and_the_entered_value_kept(
    cases: CaseService, demo_case: Case
) -> None:
    [finding] = cases.set_findings(demo_case.case_id, [_hb(102)])

    assert finding.validation_state == "ok"
    assert finding.value == 10.2
    assert finding.unit == "g/dL"
    assert finding.entered_value == "102 g/L"
    assert finding.node_id == "IBD-N3"
    assert cases.list_findings(demo_case.case_id) == [finding]
    assert cases.findings_ready(demo_case.case_id) is True


def test_non_numeric_value_or_unconvertible_unit_is_invalid(
    cases: CaseService, demo_case: Case
) -> None:
    findings = cases.set_findings(
        demo_case.case_id,
        [
            _hb("high"),
            FindingIn(kind="finding", name="CRP", value=60, unit="mmol/L"),
            _hb(10, None),
        ],
    )

    assert [f.validation_state for f in findings] == ["invalid", "invalid", "invalid"]
    assert findings[0].value == "high"
    assert findings[1].unit == "mmol/L"
    assert findings[1].entered_value == "60 mmol/L"
    assert cases.findings_ready(demo_case.case_id) is False


def test_value_outside_the_plausible_range_needs_confirmation(
    safety_cases: CaseService, demo_patient: NewPatient
) -> None:
    case = safety_cases.create_case(demo_patient, OWNER)

    [finding] = safety_cases.set_findings(case.case_id, [_hb(900)])

    assert finding.validation_state == "confirm_range"
    assert finding.value == 90
    assert safety_cases.findings_ready(case.case_id) is True


def test_two_different_hb_values_are_both_conflict(cases: CaseService, demo_case: Case) -> None:
    findings = cases.set_findings(
        demo_case.case_id,
        [_hb(102), FindingIn(kind="finding", name="haemoglobin", value=9.1, unit="g/dL")],
    )

    assert [f.validation_state for f in findings] == ["conflict", "conflict"]
    assert cases.findings_ready(demo_case.case_id) is False


def test_same_value_in_two_units_is_not_a_conflict(cases: CaseService, demo_case: Case) -> None:
    findings = cases.set_findings(demo_case.case_id, [_hb(102), _hb(10.2, "g/dL")])

    assert [f.validation_state for f in findings] == ["ok", "ok"]


def test_symptom_and_metric_without_a_node_are_ok_and_set_is_replaced(
    cases: CaseService, demo_case: Case
) -> None:
    cases.set_findings(demo_case.case_id, [_hb("high")])

    findings = cases.set_findings(
        demo_case.case_id,
        [
            FindingIn(kind="symptom", name="bloody diarrhoea", duration="3 weeks"),
            FindingIn(kind="finding", name="ferritin", value="low"),
        ],
    )

    assert [f.validation_state for f in findings] == ["ok", "ok"]
    assert findings[0].duration == "3 weeks"
    assert findings[0].node_id is None
    assert findings[1].entered_value == "low"
    assert len(cases.list_findings(demo_case.case_id)) == 2
    assert cases.findings_ready(demo_case.case_id) is True
