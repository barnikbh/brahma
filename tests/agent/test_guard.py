"""The grounding guard and claim scanner (plan Step 11; BR1, AC3.2.3, AC7.1.2, FR4.10)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from brahma.agent.engine import WalkEngine
from brahma.agent.guard import Guard
from brahma.agent.scanner import ClaimScanner, merge_claims, normalize_declared, scan_numbers
from brahma.agent.writer import node_payload
from brahma.cases import Case, CaseService, NewPatient
from brahma.knowledge import Claim, KnowledgeService, PackVersionRef
from brahma.knowledge.models import ChangeSet, Node
from tests.agent.conftest import DOCTOR

IBD = PackVersionRef(pack="IBD", number="1.2")


@pytest.fixture
def guard(knowledge: KnowledgeService, cases: CaseService) -> Guard:
    return Guard(knowledge, cases)


def _reasons(result: object) -> set[str]:
    return {f.reason for f in result.failures}  # type: ignore[attr-defined]


def test_an_exact_dose_passes(guard: Guard, demo_case: Case) -> None:
    result = guard.check_line(
        "Hydrocortisone 100 mg intravenously four times daily.",
        ["IBD-N51"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="frequency", value="four times daily")],
    )
    assert result.passed, result.failures
    assert {(c.kind, c.value) for c in result.claims} >= {
        ("dose", "100"),
        ("drug", "hydrocortisone"),
        ("frequency", "four times daily"),
    }


def test_a_declared_wrong_dose_fails(guard: Guard, demo_case: Case) -> None:
    result = guard.check_line(
        "Methylprednisolone 120 mg intravenously once daily.",
        ["IBD-N52"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="dose", value="120", unit="mg")],
    )
    assert not result.passed
    assert [(f.claim.value if f.claim else None, f.reason) for f in result.failures] == [
        ("120", "value_differs")
    ]


def test_a_declared_phrased_value_is_parsed_like_text(guard: Guard, demo_case: Case) -> None:
    dose = guard.check_line(
        "Hydrocortisone 100 mg intravenously.",
        ["IBD-N51"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="dose", value="100 mg")],
    )
    assert dose.passed, dose.failures
    tier = guard.check_line(
        "Tier 2 care in hospital.",
        ["IBD-N41"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="tier", value="Tier 2")],
    )
    assert tier.passed, tier.failures
    threshold = guard.check_line(
        "Haemoglobin below 10.5 g/dL.",
        ["IBD-N3"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="threshold", value="10.5 g/dL", unit="g/dL")],
    )
    assert threshold.passed, threshold.failures


def test_an_unparsable_declared_value_still_fails(guard: Guard, demo_case: Case) -> None:
    extent = guard.check_line(
        "Montreal E3 extent.",
        ["IBD-N41"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="tier", value="E3")],
    )
    assert not extent.passed
    vague = guard.check_line(
        "Hydrocortisone at a high dose.",
        ["IBD-N51"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="dose", value="a high dose")],
    )
    assert not vague.passed


def test_normalize_declared_keeps_exact_and_other_kinds() -> None:
    assert normalize_declared(Claim(kind="dose", value="100", unit="mg")) == Claim(
        kind="dose", value="100", unit="mg"
    )
    assert normalize_declared(Claim(kind="tier", value="2")) == Claim(kind="tier", value="2")
    drug = Claim(kind="drug", value="hydrocortisone 100 mg")
    assert normalize_declared(drug) == drug


def test_a_dose_scanned_but_not_declared_still_fails(guard: Guard, demo_case: Case) -> None:
    result = guard.check_line(
        "Methylprednisolone 120 mg once daily.",
        ["IBD-N52"],
        IBD,
        demo_case.case_id,
        declared=[Claim(kind="drug", value="methylprednisolone")],
    )
    assert not result.passed
    assert result.failures[0].claim == Claim(kind="dose", value="120", unit="mg")


def test_a_per_kg_dose_passes_as_written_or_as_computed(guard: Guard, demo_case: Case) -> None:
    per_kg = guard.check_line("Infliximab 5 mg/kg IV.", ["IBD-N53"], IBD, demo_case.case_id)
    computed = guard.check_line(
        "Infliximab 290 mg for this patient.", ["IBD-N53"], IBD, demo_case.case_id
    )
    wrong = guard.check_line("Infliximab 300 mg.", ["IBD-N53"], IBD, demo_case.case_id)
    assert per_kg.passed and computed.passed  # 5 mg/kg x 58 kg = 290 mg
    assert not wrong.passed


def test_a_per_kg_dose_without_a_weight_fails(guard: Guard, cases: CaseService) -> None:
    case = cases.create_case(
        NewPatient(synthetic_name="No Weight (synthetic)", age=40, sex="male"), DOCTOR
    )
    result = guard.check_line("Infliximab 290 mg.", ["IBD-N53"], IBD, case.case_id)
    assert not result.passed


def test_a_line_must_cite_a_walked_node_of_the_version(guard: Guard, demo_case: Case) -> None:
    none = guard.check_line("Rest and fluids.", [], IBD, demo_case.case_id)
    unknown = guard.check_line("Rest and fluids.", ["IBD-N999"], IBD, demo_case.case_id)
    not_walked = guard.check_line(
        "Diet advice.", ["IBD-N60"], IBD, demo_case.case_id, allowed_node_ids=["IBD-N61"]
    )
    no_claims = guard.check_line("Diet advice.", ["IBD-N60"], IBD, demo_case.case_id)
    assert _reasons(none) == {"no_cited_node"}
    assert _reasons(unknown) == {"node_not_in_version", "no_cited_node"}
    assert "node_not_walked" in _reasons(not_walked)
    assert no_claims.passed


def test_a_name_claim_must_match_a_cited_node(guard: Guard, demo_case: Case) -> None:
    result = guard.check_line(
        "Consider infliximab now.", ["IBD-N51"], IBD, demo_case.case_id
    )  # the cited node is hydrocortisone
    assert not result.passed
    assert result.failures[0].claim == Claim(kind="drug", value="infliximab")


def test_a_guard_exception_fails_the_line(
    guard: Guard, demo_case: Case, monkeypatch: pytest.MonkeyPatch, knowledge: KnowledgeService
) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(knowledge, "match_claims", broken)
    monkeypatch.setattr(knowledge, "sources", broken)
    result = guard.check_line("Hydrocortisone 100 mg.", ["IBD-N51"], IBD, demo_case.case_id)
    assert not result.passed
    assert result.error == "RuntimeError"
    assert _reasons(result) == {"guard_error"}
    by_source = guard.check_line_by_source("Hydrocortisone 100 mg.", ["IBD-S2"], IBD, None)
    assert by_source.error == "RuntimeError"


def test_check_line_by_source_passes_and_fails(guard: Guard, demo_case: Case) -> None:
    ok = guard.check_line_by_source(
        "Methylprednisolone 60 mg IV once daily.", ["IBD-S2"], IBD, demo_case.case_id
    )
    wrong = guard.check_line_by_source(
        "Methylprednisolone 120 mg IV once daily.", ["IBD-S2"], IBD, demo_case.case_id
    )
    unknown = guard.check_line_by_source("Rest.", ["XYZ-S1"], IBD, demo_case.case_id)
    none = guard.check_line_by_source("Rest.", [], IBD, demo_case.case_id)
    no_claims = guard.check_line_by_source("Rest and review.", ["IBD-S2"], IBD, None)
    per_kg = guard.check_line_by_source("Infliximab 290 mg.", ["IBD-S1"], IBD, demo_case.case_id)
    assert ok.passed and no_claims.passed and per_kg.passed
    assert _reasons(wrong) == {"no_supporting_node"}
    assert _reasons(unknown) == {"source_not_in_pack"}
    assert _reasons(none) == {"no_cited_source"}


def test_scanner_finds_numbers_and_longest_names(knowledge: KnowledgeService) -> None:
    scanner = ClaimScanner(knowledge)
    claims = scanner.scan(
        "Acute severe ulcerative colitis: methylprednisolone 60 mg/day, CRP above 45 mg/L, "
        "infliximab 5 mg/kg; 5-ASA is not used.",
        IBD,
    )
    found = {(c.kind, c.value, c.unit) for c in claims}
    assert ("diagnosis", "acute severe ulcerative colitis", None) in found
    assert ("diagnosis", "ulcerative colitis", None) not in found
    assert {("dose", "60", "mg/day"), ("threshold", "45", "mg/L"), ("dose", "5", "mg/kg")} <= found
    assert ("drug", "5-asa", None) in found
    assert scanner.vocabulary(IBD) is scanner.vocabulary(IBD)  # cached per version
    assert scan_numbers("day 3, 4 to 7 days") == []
    merged = merge_claims([Claim(kind="dose", value="60", unit="mg")], scan_numbers("60 MG"))
    assert len(merged) == 1


def _band_version(knowledge: KnowledgeService) -> PackVersionRef:
    """IBD 1.3 with a weight-band drug node citing IBD-S5."""
    base = knowledge.get_node(IBD, "IBD-N54").model_dump(by_alias=True, exclude={"pack_version"})
    bands = [
        {"weightMaxKg": 55, "doseValue": 260, "doseUnit": "mg"},
        {"weightMinKg": 55, "weightMaxKg": 85, "doseValue": 390, "doseUnit": "mg"},
        {"weightMinKg": 85, "doseValue": 520, "doseUnit": "mg"},
    ]
    fields = {**base["fields"], "doseBasis": "weight_band", "doseValue": 260, "doseBands": bands}
    node = Node.model_validate(
        {**base, "nodeId": "IBD-N112", "fields": fields, "sourceIds": ["IBD-S5"]}
    )
    change = ChangeSet(add_nodes=[node], change_summary="Add a weight-band node.")
    return knowledge.create_version("IBD", IBD, change, "seed")


def test_a_weight_band_dose_must_be_this_patients_band(
    guard: Guard, knowledge: KnowledgeService, cases: CaseService, demo_patient: NewPatient
) -> None:
    version = _band_version(knowledge)
    case = cases.create_case(demo_patient, DOCTOR)  # 58 kg, so the middle band
    good = guard.check_line("Ustekinumab 390 mg.", ["IBD-N112"], version, case.case_id)
    assert good.passed, good.failures
    wrong = guard.check_line("Ustekinumab 260 mg.", ["IBD-N112"], version, case.case_id)
    assert not wrong.passed and "value_differs" in _reasons(wrong)
    by_source = guard.check_line_by_source("Ustekinumab 520 mg.", ["IBD-S5"], version, case.case_id)
    assert not by_source.passed


def test_any_stated_band_passes_until_a_weight_is_known(
    guard: Guard, knowledge: KnowledgeService, cases: CaseService
) -> None:
    version = _band_version(knowledge)
    case = cases.create_case(
        NewPatient(synthetic_name="No Weight (synthetic)", age=40, sex="male"), DOCTOR
    )
    assert guard.check_line("Ustekinumab 520 mg.", ["IBD-N112"], version, case.case_id).passed
    assert not guard.check_line("Ustekinumab 615 mg.", ["IBD-N112"], version, case.case_id).passed


def test_the_writer_sees_only_this_patients_band_once_the_weight_is_known(
    make_engine: Callable[..., WalkEngine],
    knowledge: KnowledgeService,
    cases: CaseService,
    demo_patient: NewPatient,
) -> None:
    node = knowledge.get_node(_band_version(knowledge), "IBD-N112")
    engine = make_engine()
    case = cases.create_case(demo_patient, DOCTOR)  # 58 kg
    fields = engine._one_band(case.case_id, node_payload(node))["fields"]
    assert fields["doseValue"] == 390 and "doseBands" not in fields
    unweighed = cases.create_case(
        NewPatient(synthetic_name="No Weight (synthetic)", age=40, sex="male"), DOCTOR
    )
    assert len(engine._one_band(unweighed.case_id, node_payload(node))["fields"]["doseBands"]) == 3
    other = knowledge.get_node(IBD, "IBD-N51")
    assert engine._one_band(case.case_id, node_payload(other))["fields"] == other.fields
