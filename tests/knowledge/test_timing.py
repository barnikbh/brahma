"""Timing budgets (NFR1.1: search and neighbours under 50 ms at 2,000 nodes; NFR10.1: both
real packs load in under 2 s). Marked ``timing``; the 2,000-node pack is generated here."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from brahma.knowledge import Fact, KnowledgeService, PackVersionRef

pytestmark = pytest.mark.timing

NODE_COUNT = 2000
BUDGET_S = 0.050
FAN_OUT = 60


def _node(i: int) -> dict[str, Any]:
    kind = ("symptom", "metric", "test", "diagnosis")[i % 4]
    fields: dict[str, Any] = {
        "symptom": {"name": f"symptom {i}", "synonyms": [f"synonym {i}"]},
        "metric": {"measure": f"measure {i}", "unit": "mg", "threshold": 5, "comparator": "gt"},
        "test": {"name": f"test {i}", "resultOptions": ["positive", "negative"]},
        "diagnosis": {"name": f"diagnosis {i}"},
    }[kind]
    column = {"symptom": "findings", "metric": "findings", "test": "tests"}.get(kind, "diagnosis")
    return {
        "nodeId": f"PRF-N{i}",
        "type": kind,
        "label": f"Node {i}",
        "content": "Generated node for timing.",
        "fields": fields,
        "sourceIds": ["PRF-S1"],
        "column": column,
    }


def _edges() -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for i in range(1, NODE_COUNT):
        edge: dict[str, Any] = {
            "edgeId": f"PRF-E{i}",
            "fromNodeId": f"PRF-N{i}",
            "toNodeId": f"PRF-N{i + 1}",
            "relation": "suggests",
        }
        test_index = i - (i % 4) + 2
        if 0 < test_index <= NODE_COUNT:
            edge["condition"] = {
                "test": f"test {test_index}",
                "comparator": "eq",
                "value": "positive",
            }
        edges.append(edge)
    for j in range(FAN_OUT):
        edges.append(
            {
                "edgeId": f"PRF-F{j}",
                "fromNodeId": "PRF-N4",
                "toNodeId": f"PRF-N{100 + j}",
                "relation": "refines_to",
                "condition": {"finding": "measure 1", "comparator": "gt", "value": 5, "unit": "g"},
            }
        )
    return edges


@pytest.fixture
def big_pack(write_pack: Callable[..., Path]) -> Path:
    pack = {
        "pack": {"code": "PRF", "name": "Timing pack", "specialty": "Testing"},
        "version": "1.0",
        "sources": [{"sourceId": "PRF-S1", "title": "Generated", "year": 2024, "section": "1"}],
        "nodes": [_node(i) for i in range(1, NODE_COUNT + 1)],
        "edges": _edges(),
    }
    return write_pack(pack, "timing.yaml")


def _median_seconds(call: Callable[[], object], runs: int = 20) -> float:
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        call()
        samples.append(time.perf_counter() - started)
    return statistics.median(samples)


FACTS = [Fact(kind="finding", name=f"synonym {i}") for i in range(1, NODE_COUNT, 100)] + [
    Fact(kind="test", name="measure 1", value="0.01", unit="g"),
    Fact(kind="test", name="test 2", value="positive"),
]


def test_search_and_neighbours_under_50ms(service: KnowledgeService, big_pack: Path) -> None:
    version = service.load_pack(big_pack)
    assert len(service.search(version, FACTS).matches) > 0
    steps = service.neighbours(version, "PRF-N4", FACTS)
    assert len(steps) == FAN_OUT + 1
    assert _median_seconds(lambda: service.search(version, FACTS)) < BUDGET_S
    assert _median_seconds(lambda: service.neighbours(version, "PRF-N4", FACTS)) < BUDGET_S


def test_cold_index_built_at_open_not_first_call(big_pack: Path, tmp_db: Path) -> None:
    loader = KnowledgeService.open(tmp_db)
    version = loader.load_pack(big_pack)
    loader.close()
    started = time.perf_counter()
    cold = KnowledgeService.open(tmp_db)
    try:
        build_seconds = time.perf_counter() - started
        assert "PRF@1.0" in cold._indexes
        first_call = time.perf_counter()
        cold.neighbours(version, "PRF-N4", FACTS)
        assert time.perf_counter() - first_call < BUDGET_S
        assert build_seconds < 2.0  # opening with a warm build fits the app-start budget
    finally:
        cold.close()


def test_real_packs_load_under_2s(service: KnowledgeService) -> None:
    content = Path(__file__).resolve().parents[2] / "content"
    started = time.perf_counter()
    refs = [service.load_pack(content / "ibd.yaml"), service.load_pack(content / "urology.yaml")]
    assert time.perf_counter() - started < 2.0
    assert [r.pack for r in refs] == ["IBD", "URO"]
    assert isinstance(refs[0], PackVersionRef)
