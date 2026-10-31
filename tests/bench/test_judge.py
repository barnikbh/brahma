"""The benchmark judge: grounded share and pathway agreement (FR13.4-FR13.6)."""

from __future__ import annotations

from brahma.bench import LineVerdict, agreement, graph_grounded_share, judge_plain_line
from brahma.knowledge.models import Claim, Node


def _drug() -> Node:
    return Node(
        node_id="T-N1",
        type="drug",
        label="Test drug 100 mg",
        content="A test drug.",
        fields={"drug": "testdrug", "doseValue": 100, "doseUnit": "mg", "doseBasis": "absolute"},
        source_ids=["T-S1"],
        column="treatment",
    )


def _other() -> Node:
    return Node(
        node_id="T-N2",
        type="drug",
        label="Other drug 40 mg",
        content="Another test drug.",
        fields={"drug": "otherdrug", "doseValue": 40, "doseUnit": "mg", "doseBasis": "absolute"},
        source_ids=["T-S2"],
        column="treatment",
    )


def test_graph_share_is_cited_over_total() -> None:
    assert graph_grounded_share(30, 0) == 1.0
    assert graph_grounded_share(29, 1) == 29 / 30
    assert graph_grounded_share(0, 0) is None


def test_agreement_is_supporting_over_expected() -> None:
    assert agreement({"A", "B"}, {"A", "B", "C"}) == 2 / 3
    assert agreement(set(), {"A"}) == 0.0
    assert agreement(set(), set()) == 1.0


def test_plain_line_needs_a_pack_source_and_support_under_it() -> None:
    drug, other = _drug(), _other()
    by_source = {"T-S1": [drug], "T-S2": [other]}
    dose = [Claim(kind="dose", value="100", unit="mg")]
    assert judge_plain_line(dose, ["T-S1"], by_source, {"T-S1", "T-S2"}, [drug, other]) == (
        LineVerdict(grounded=True, supporting=("T-N1",))
    )
    wrong_source = judge_plain_line(dose, ["T-S2"], by_source, {"T-S1", "T-S2"}, [drug, other])
    assert wrong_source.grounded is False
    assert wrong_source.supporting == ("T-N1",)
    assert (
        judge_plain_line(dose, ["T-S9"], by_source, {"T-S1", "T-S2"}, [drug, other]).grounded
        is False
    )
    assert judge_plain_line(dose, [], by_source, {"T-S1", "T-S2"}, [drug, other]).grounded is False


def test_plain_line_with_no_claims_is_not_grounded() -> None:
    drug = _drug()
    verdict = judge_plain_line([], ["T-S1"], {"T-S1": [drug]}, {"T-S1"}, [drug])
    assert verdict == LineVerdict(grounded=False, supporting=())


def test_plain_line_needs_every_claim_supported() -> None:
    drug = _drug()
    by_source = {"T-S1": [drug]}
    claims = [Claim(kind="dose", value="100", unit="mg"), Claim(kind="dose", value="40", unit="mg")]
    verdict = judge_plain_line(claims, ["T-S1"], by_source, {"T-S1"}, [drug])
    assert verdict.grounded is False
    assert verdict.supporting == ("T-N1",)
