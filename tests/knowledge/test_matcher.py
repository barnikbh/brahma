"""Claim matching and unit conversion (Step 10): exact, Decimal-based, no tolerance."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from brahma.knowledge import Claim, KnowledgeService, Node, PackVersionRef
from brahma.knowledge.matcher import natural_key, normalise_text
from brahma.knowledge.units import compare, convert, normalise_unit, to_decimal


@pytest.fixture
def loaded(service: KnowledgeService, minimal_pack_path: Path) -> PackVersionRef:
    return service.load_pack(minimal_pack_path)


def _node(service: KnowledgeService, version: PackVersionRef, node_id: str) -> Node:
    return service.get_node(version, node_id)


def _reasons(service: KnowledgeService, node: Node, *claims: Claim) -> list[str]:
    return [f.reason for f in service.match_claims(node, claims).failures]


def test_exact_dose_matches_and_near_miss_fails(
    service: KnowledgeService, loaded: PackVersionRef
) -> None:
    drug = _node(service, loaded, "TST-N8")
    exact = Claim(kind="dose", value="60", unit="mg")
    as_grams = Claim(kind="dose", value="0.06", unit="g")
    near = Claim(kind="dose", value="60.4", unit="mg")
    double = Claim(kind="dose", value="120", unit="mg")
    result = service.match_claims(drug, [exact, as_grams, near, double])
    assert result.matched == [exact, as_grams]
    assert [f.reason for f in result.failures] == ["value_differs", "value_differs"]


def test_hb_in_g_per_l_matches_g_per_dl_exactly(
    service: KnowledgeService, loaded: PackVersionRef
) -> None:
    hb = _node(service, loaded, "TST-N3")
    assert convert(Decimal("102"), "g/L", "g/dL", "Hb") == Decimal("10.2")
    assert _reasons(service, hb, Claim(kind="threshold", value="105", unit="g/L")) == []
    assert _reasons(service, hb, Claim(kind="threshold", value="10.5", unit="g/dL")) == []
    assert _reasons(service, hb, Claim(kind="threshold", value="104", unit="g/L")) == [
        "value_differs"
    ]
    calprotectin = _node(service, loaded, "TST-N10")
    assert _reasons(service, calprotectin, Claim(kind="threshold", value="50", unit="mg/kg")) == []


def test_drug_synonym_and_text_normalisation(
    service: KnowledgeService, loaded: PackVersionRef
) -> None:
    drug = _node(service, loaded, "TST-N8")
    claims = [
        Claim(kind="drug", value="  SoluMedrol "),
        Claim(kind="drug", value="METHYLPREDNISOLONE"),
        Claim(kind="frequency", value="Once   daily"),
        Claim(kind="drug", value="prednisolone"),
    ]
    result = service.match_claims(drug, claims)
    assert len(result.matched) == 3
    assert [f.reason for f in result.failures] == ["value_differs"]
    assert normalise_text("  Bloody\tStool ") == "bloody stool"


def test_unknown_unit_and_kind_without_field(
    service: KnowledgeService, loaded: PackVersionRef
) -> None:
    drug = _node(service, loaded, "TST-N8")
    assert _reasons(
        service,
        drug,
        Claim(kind="dose", value="60", unit="tablets"),
        Claim(kind="dose", value="sixty", unit="mg"),
        Claim(kind="threshold", value="60", unit="mg"),
        Claim(kind="tier", value="2"),
    ) == ["unknown_unit", "value_not_a_number", "no_field_for_kind", "no_field_for_kind"]
    tier = _node(service, loaded, "TST-N7")
    assert _reasons(
        service, tier, Claim(kind="tier", value="2"), Claim(kind="tier", value="3")
    ) == ["value_differs"]
    assert _reasons(service, tier, Claim(kind="tier", value="two")) == ["value_not_a_number"]


def test_per_kg_node_refuses_absolute_dose_claim(
    service: KnowledgeService, loaded: PackVersionRef
) -> None:
    infliximab = _node(service, loaded, "TST-N9")
    assert _reasons(service, infliximab, Claim(kind="dose", value="350", unit="mg")) == [
        "dose_basis_per_kg"
    ]
    assert _reasons(service, infliximab, Claim(kind="drug", value="Remicade")) == []
    diagnosis = _node(service, loaded, "TST-N4")
    assert _reasons(service, diagnosis, Claim(kind="diagnosis", value="ulcerative colitis")) == []
    test = _node(service, loaded, "TST-N6")
    assert _reasons(service, test, Claim(kind="test", value="Stool Culture")) == []


def test_find_supporting_node(service: KnowledgeService, loaded: PackVersionRef) -> None:
    dose = [
        Claim(kind="drug", value="methylprednisolone"),
        Claim(kind="dose", value="60", unit="mg"),
    ]
    found = service.find_supporting_node(loaded, "TST-S1", dose)
    assert found is not None and found.node_id == "TST-N8"
    assert (
        service.find_supporting_node(loaded, "TST-S2", [Claim(kind="drug", value="aspirin")])
        is None
    )
    assert service.find_supporting_node(loaded, "TST-S1", []) is None
    assert service.find_supporting_node(loaded, "TST-S404", dose) is None


def test_unit_helpers() -> None:
    assert normalise_unit(" µg/g ") == "ug/g" == normalise_unit("mcg/g")
    assert convert(Decimal(1), None, None) == Decimal(1)
    assert convert(Decimal(1), "mg", None) is None
    assert convert(Decimal(2), "weeks", "days") == Decimal(14)
    assert convert(Decimal(5), "mg", "g", "Hb") is None
    assert to_decimal(True) is None
    assert to_decimal("nan") is None
    assert to_decimal("x") is None
    assert to_decimal(object()) is None
    assert to_decimal(10.2) == Decimal("10.2")
    assert compare(Decimal(1), "le", Decimal(1)) and compare(Decimal(2), "ge", Decimal(1))
    with pytest.raises(ValueError, match="unknown comparator"):
        compare(Decimal(1), "ne", Decimal(1))
    assert sorted(["IBD-N10", "IBD-N2", "X"], key=natural_key) == ["IBD-N2", "IBD-N10", "X"]
