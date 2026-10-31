"""PackValidator (Step 10): sources, IDs, fields, edges, placeholders and the patient-data scan."""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from brahma.knowledge import Fact, KnowledgeService, PackLoadError
from brahma.knowledge.validator import find_patient_data


@pytest.mark.parametrize(
    ("fixture", "item_id", "reason"),
    [
        ("sourceless.yaml", "TST-N1", "sourceIds"),
        ("cross_pack_id.yaml", "IBD-N1", "must start with the pack code TST-"),
        ("placeholder.yaml", "TST-N1", "placeholder [60 mg]"),
        ("email.yaml", "TST-N1", "email address"),
        ("date.yaml", "TST-N1", "looks like a date: 12/03/1990"),
    ],
)
def test_bad_fixture_refused_and_nothing_stored(
    service: KnowledgeService, fixtures_dir: Path, fixture: str, item_id: str, reason: str
) -> None:
    with pytest.raises(PackLoadError) as caught:
        service.load_pack(fixtures_dir / fixture)
    assert caught.value.item_id == item_id
    assert reason in caught.value.reason
    assert service.list_versions("TST") == []


def test_unknown_source_refused(
    service: KnowledgeService, minimal_pack: dict[str, Any], write_pack: Callable[..., Path]
) -> None:
    minimal_pack["nodes"][0]["sourceIds"] = ["TST-S9"]
    with pytest.raises(PackLoadError, match="unknown source TST-S9") as caught:
        service.load_pack(write_pack(minimal_pack))
    assert caught.value.item_id == "TST-N1"


def test_missing_drug_field_refused(
    service: KnowledgeService, minimal_pack: dict[str, Any], write_pack: Callable[..., Path]
) -> None:
    del minimal_pack["nodes"][7]["fields"]["doseBasis"]
    with pytest.raises(PackLoadError, match="missing field doseBasis") as caught:
        service.load_pack(write_pack(minimal_pack))
    assert caught.value.item_id == "TST-N8"


@pytest.mark.parametrize(
    ("mutate", "item_id", "reason"),
    [
        (lambda p: p["edges"][0].update(toNodeId="TST-N99"), "TST-E1", "not in this version"),
        (lambda p: p["edges"][0].update(toNodeId="TST-N1"), "TST-E1", "self-edge"),
        (lambda p: p["edges"].append(dict(p["edges"][0])), "TST-E1", "duplicate edge"),
        (lambda p: p["edges"][0].update(edgeId="E1"), "E1", "must start with TST-"),
        (
            lambda p: p["edges"][3]["condition"].update(test="biopsy"),
            "TST-E4",
            "unknown finding/test biopsy",
        ),
        (
            lambda p: p["edges"][3]["condition"].update(value="maybe"),
            "TST-E4",
            "not a result option",
        ),
        (
            lambda p: p["edges"][3]["condition"].update(comparator="lt"),
            "TST-E4",
            "must use eq",
        ),
        (
            lambda p: p["edges"][4]["condition"].update(unit="mmol/L"),
            "TST-E5",
            "unit mmol/L is unknown",
        ),
        (lambda p: p["nodes"].append(copy.deepcopy(p["nodes"][0])), "TST-N1", "duplicate node"),
        (lambda p: p["sources"][0].update(sourceId="S1"), "S1", "must start with TST-"),
        (lambda p: p["sources"].append(dict(p["sources"][0])), "TST-S1", "duplicate source"),
        (
            lambda p: p["nodes"][6]["fields"].update(drugNodeIds=["TST-N1"]),
            "TST-N7",
            "not a drug",
        ),
        (
            lambda p: p["nodes"][0].update(referenceRanges=[{"low": 1, "unit": "g/dL"}]),
            "TST-N1",
            "only metric",
        ),
    ],
)
def test_malformed_graph_refused(
    service: KnowledgeService,
    minimal_pack: dict[str, Any],
    write_pack: Callable[..., Path],
    mutate: Callable[[dict[str, Any]], None],
    item_id: str,
    reason: str,
) -> None:
    mutate(minimal_pack)
    with pytest.raises(PackLoadError) as caught:
        service.load_pack(write_pack(minimal_pack))
    assert (caught.value.item_id, reason in caught.value.reason) == (item_id, True)


@pytest.mark.parametrize(
    "text",
    [
        "Infliximab at weeks 0, 2 and 6, then every 8 weeks.",
        "Taper 40-30-20 mg over three weeks.",
        "Induction at weeks 0-2-6.",
        "Guideline published in 2022, section 5.",
    ],
)
def test_clinical_schedules_allowed(text: str) -> None:
    assert find_patient_data(text) is None


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("Born 1990-03-12.", "ISO date"),
        ("Hospital number 123456789.", "8 or more digits"),
        ("Seen 3-4-2021 in clinic.", "date"),
    ],
)
def test_patient_like_text_flagged(text: str, problem: str) -> None:
    found = find_patient_data(text)
    assert found is not None and problem in found


def test_minimal_pack_is_valid(service: KnowledgeService, minimal_pack_path: Path) -> None:
    ref = service.load_pack(minimal_pack_path)
    assert (ref.pack, ref.number) == ("TST", "1.0")


def _therapy(p: dict[str, Any], **condition: Any) -> None:
    """Put a therapy condition on the tier -> infliximab edge (TST-E7)."""
    p["edges"][6]["condition"] = {"comparator": "eq", **condition}


@pytest.mark.parametrize(
    ("condition", "reason"),
    [
        ({"therapy": "adalimumab", "value": "failed"}, "unknown therapy adalimumab"),
        ({"therapy": "infliximab", "value": "maybe"}, "not a therapy response"),
        ({"therapy": "anti-TNF", "value": "failed", "comparator": "lt"}, "must use eq"),
    ],
)
def test_a_bad_therapy_condition_is_refused(
    service: KnowledgeService,
    minimal_pack: dict[str, Any],
    write_pack: Callable[..., Path],
    condition: dict[str, Any],
    reason: str,
) -> None:
    _therapy(minimal_pack, **condition)
    with pytest.raises(PackLoadError) as caught:
        service.load_pack(write_pack(minimal_pack))
    assert (caught.value.item_id, reason in caught.value.reason) == ("TST-E7", True)


def test_a_condition_names_exactly_one_fact(
    service: KnowledgeService, minimal_pack: dict[str, Any], write_pack: Callable[..., Path]
) -> None:
    _therapy(minimal_pack, therapy="infliximab", test="biopsy", value="failed")
    with pytest.raises(PackLoadError, match="exactly one of finding, test or therapy"):
        service.load_pack(write_pack(minimal_pack))


def test_a_therapy_condition_matches_by_drug_synonym_or_class(
    service: KnowledgeService, minimal_pack: dict[str, Any], write_pack: Callable[..., Path]
) -> None:
    _therapy(minimal_pack, therapy="anti-TNF", value="failed")
    version = service.load_pack(write_pack(minimal_pack))

    def status(*facts: Fact) -> str:
        steps = service.neighbours(version, "TST-N7", list(facts), "offers_drug")
        return next(s.status for s in steps if s.node.node_id == "TST-N9")

    assert status() == "not_taken"  # no history: not taken, never asked for
    assert status(Fact(kind="therapy", name="infliximab", value="failed")) == "followable"
    assert status(Fact(kind="therapy", name="anti-TNF", value="failed")) == "followable"
    assert status(Fact(kind="therapy", name="infliximab", value="responded")) == "not_taken"
    assert status(Fact(kind="therapy", name="methylprednisolone", value="failed")) == "not_taken"
