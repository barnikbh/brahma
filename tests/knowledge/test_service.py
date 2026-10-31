"""Index and KnowledgeService (Step 10): search, neighbours, ranges, versions, logging."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from brahma.knowledge import (
    BaseNotLive,
    ChangeSet,
    Edge,
    Fact,
    KnowledgeService,
    Node,
    NodeNotFound,
    PackLoadError,
    PackVersionRef,
    VersionNotFound,
    VersionNotIncreasing,
    VersionRequired,
)


@pytest.fixture
def v1(service: KnowledgeService, minimal_pack_path: Path) -> PackVersionRef:
    return service.load_pack(minimal_pack_path)


def _ids(nodes: list[Node]) -> list[str]:
    return [n.node_id for n in nodes]


def test_search_by_synonym_duration_and_metric(
    service: KnowledgeService, v1: PackVersionRef
) -> None:
    result = service.search(
        v1,
        [
            Fact(kind="finding", name="Blood in stool"),
            Fact(kind="finding", name="abdominal pain", value=4, unit="weeks"),
            Fact(kind="test", name="haemoglobin", value=102, unit="g/L"),
            Fact(kind="test", name="calprotectin", value=40, unit="ug/g"),
            Fact(kind="finding", name="unknown thing"),
        ],
    )
    assert _ids(result.matches) == ["TST-N1", "TST-N3"]
    assert result.unknown_unit == []
    longer = service.search(v1, [Fact(kind="finding", name="Tummy pain", value=2, unit="months")])
    assert longer.matches == [] and len(longer.unknown_unit) == 1
    six = service.search(v1, [Fact(kind="finding", name="abdominal pain", value=42, unit="days")])
    assert _ids(six.matches) == ["TST-N2"]
    weird = service.search(v1, [Fact(kind="test", name="Hb", value=6, unit="mmol/L")])
    assert weird.matches == [] and weird.unknown_unit[0].unit == "mmol/L"


def test_neighbours_statuses(service: KnowledgeService, v1: PackVersionRef) -> None:
    no_facts = {s.edge.edge_id: s.status for s in service.neighbours(v1, "TST-N4", [])}
    assert no_facts == {"TST-E2": "followable", "TST-E3": "alternative", "TST-E4": "unknown_input"}
    negative = [Fact(kind="test", name="Stool culture", value="Negative")]
    positive = [Fact(kind="test", name="stool culture", value="positive")]
    assert service.neighbours(v1, "TST-N4", negative, "first_line")[0].status == "followable"
    assert service.neighbours(v1, "TST-N4", positive, "first_line")[0].status == "not_taken"
    low = [Fact(kind="test", name="Hb", value=102, unit="g/L")]
    normal = [Fact(kind="test", name="hemoglobin", value=13, unit="g/dL")]
    odd_unit = [Fact(kind="test", name="Hb", value=6, unit="mmol/L")]
    assert service.neighbours(v1, "TST-N3", low)[0].status == "followable"
    assert service.neighbours(v1, "TST-N3", normal)[0].status == "not_taken"
    assert service.neighbours(v1, "TST-N3", odd_unit)[0].status == "unknown_input"
    step = service.neighbours(v1, "TST-N1", [])[0]
    assert (step.node.node_id, step.node.pack_version) == ("TST-N4", v1)
    with pytest.raises(NodeNotFound):
        service.neighbours(v1, "TST-N404", [])


def test_reference_range_precedence_and_unknown_sex(
    service: KnowledgeService, v1: PackVersionRef
) -> None:
    female = service.reference_range(v1, "TST-N3", "female", 40, False)
    assert female is not None and (female.range.low, female.flags) == (12, [])
    pregnant = service.reference_range(v1, "TST-N3", "female", 30, True)
    assert pregnant is not None and pregnant.range.low == 11
    male = service.reference_range(v1, "TST-N3", "male", 50, None)
    assert male is not None and male.range.low == 13
    child = service.reference_range(v1, "TST-N3", "female", 3, None)
    assert child is not None and child.range.sex == "female"
    unknown = service.reference_range(v1, "TST-N3", None, 40, None)
    assert unknown is not None
    assert (unknown.range.low, unknown.flags) == (12, ["sex_not_recorded"])
    assert service.reference_range(v1, "TST-N1", "female", 40, None) is None
    assert service.reference_range(v1, "TST-N1", None, 40, None) is None


def test_reload_same_or_lower_version_refused(
    service: KnowledgeService,
    v1: PackVersionRef,
    minimal_pack: dict[str, Any],
    write_pack: Callable[..., Path],
) -> None:
    with pytest.raises(VersionNotIncreasing):
        service.load_pack(write_pack(minimal_pack))
    minimal_pack["version"] = "1.1"
    minimal_pack["changeSummary"] = "Reworded"
    v11 = service.load_pack(write_pack(minimal_pack))
    versions = service.list_versions("TST")
    assert [(v.number, v.status, v.change_summary) for v in versions] == [
        ("1.1", "live", "Reworded"),
        ("1.0", "superseded", "Initial test pack"),
    ]
    assert service.live_version("TST") == v11
    assert service.get_node(v1, "TST-N1").pack_version == v1


def test_create_version_supersedes_and_revalidates(
    service: KnowledgeService, v1: PackVersionRef
) -> None:
    base_node = service.get_node(v1, "TST-N4")
    changes = ChangeSet(
        update_nodes=[base_node.model_copy(update={"label": "Ulcerative colitis (UC)"})],
        remove_edge_ids=["TST-E3"],
        add_edges=[
            Edge(edge_id="TST-E8", from_node_id="TST-N2", to_node_id="TST-N4", relation="suggests")
        ],
        change_summary="Relabel UC",
    )
    v11 = service.create_version("TST", v1, changes, "reviewer-1")
    assert v11 == PackVersionRef(pack="TST", number="1.1")
    assert service.get_node(v11, "TST-N4").label == "Ulcerative colitis (UC)"
    assert service.get_node(v1, "TST-N4").label == "Ulcerative colitis"
    assert [s.edge.edge_id for s in service.neighbours(v11, "TST-N4", [])] == ["TST-E2", "TST-E4"]
    latest = service.list_versions("TST")[0]
    assert (latest.published_by, latest.based_on, latest.status) == (
        "reviewer-1",
        "TST@1.0",
        "live",
    )
    with pytest.raises(BaseNotLive):
        service.create_version("TST", v1, changes, "reviewer-1")
    bad = ChangeSet(remove_node_ids=["TST-N8"], change_summary="Remove drug")
    with pytest.raises(PackLoadError):
        service.create_version("TST", v11, bad, "reviewer-1")
    for broken in (
        ChangeSet(add_nodes=[base_node], change_summary="dup"),
        ChangeSet(
            update_nodes=[base_node.model_copy(update={"node_id": "TST-N99"})], change_summary="x"
        ),
        ChangeSet(remove_edge_ids=["TST-E99"], change_summary="x"),
    ):
        with pytest.raises(PackLoadError):
            service.create_version("TST", v11, broken, "reviewer-1")
    with pytest.raises(PackLoadError, match="belongs to pack"):
        service.create_version("URO", v11, bad, "reviewer-1")
    assert service.live_version("TST") == v11


def test_one_log_line_per_load_and_version(
    service: KnowledgeService, minimal_pack_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="brahma.knowledge")
    v1 = service.load_pack(minimal_pack_path)
    with pytest.raises(VersionNotIncreasing):
        service.load_pack(minimal_pack_path)
    service.create_version("TST", v1, ChangeSet(change_summary="No-op"), "reviewer-1")
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "brahma.knowledge"]
    assert [(e["event"], e["result"]) for e in lines] == [
        ("load_pack", "ok"),
        ("load_pack", "error"),
        ("create_version", "ok"),
    ]
    first = lines[0]
    assert {"event", "pack", "version", "nodes", "durationMs", "result"} <= set(first)
    assert (first["pack"], first["version"], first["nodes"]) == ("TST", "1.0", 10)
    assert "VersionNotIncreasing" in lines[1]["error"]
    assert lines[2]["version"] == "1.1"


def test_reads_require_a_known_version(service: KnowledgeService, v1: PackVersionRef) -> None:
    with pytest.raises(VersionRequired):
        service.search(None, [])  # type: ignore[arg-type]
    with pytest.raises(VersionNotFound):
        service.get_node(PackVersionRef(pack="TST", number="9.9"), "TST-N1")
    with pytest.raises(VersionNotFound):
        service.live_version("URO")
    with pytest.raises(NodeNotFound):
        service.get_node(v1, "TST-N404")


def test_subgraph_sources_comments_and_warm_reopen(
    service: KnowledgeService, v1: PackVersionRef, tmp_db: Path
) -> None:
    graph = service.subgraph(v1, ["TST-N4", "TST-N6", "TST-N5", "TST-N4", "TST-N404"])
    assert _ids(graph.nodes) == ["TST-N4", "TST-N6", "TST-N5"]
    assert [e.edge_id for e in graph.edges] == ["TST-E2", "TST-E3"]
    assert graph.missing == ["TST-N404"]
    assert graph.nodes[2].alternative is True and graph.nodes[1].column == "tests"
    assert [s.source_id for s in service.sources(v1)] == ["TST-S1", "TST-S2"]
    comment_id = service.add_comment("TST-N4", "doctor-1", "Check extent first")
    assert [c.comment_id for c in service.list_comments("TST-N4")] == [comment_id]
    reopened = KnowledgeService.open(tmp_db)
    try:
        assert "TST@1.0" in reopened._indexes  # built at start, not on first call
        assert reopened.get_node(v1, "TST-N4").label == "Ulcerative colitis"
    finally:
        reopened.close()
