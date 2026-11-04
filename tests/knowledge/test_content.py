"""Content packs (Step 14): both packs validate, the demo walks reach their nodes, the
alternative branch is present, the urology stub walks, and the copy check flags long runs.

These are integration tests over the real files in ``content/``.
"""

from __future__ import annotations

import importlib.util
from collections import deque
from pathlib import Path
from types import ModuleType

import pytest

from brahma.knowledge import Fact, KnowledgeService, PackVersionRef
from brahma.knowledge.validate import main as validate_main

from .conftest import CONTENT, FIXTURES, PROJECT_ROOT

IBD = CONTENT / "ibd.yaml"
URO = CONTENT / "urology.yaml"


def _walk(service: KnowledgeService, version: PackVersionRef, facts: list[Fact]) -> set[str]:
    """Follow every followable step from the search entry points; return reached node IDs."""
    queue = deque(n.node_id for n in service.search(version, facts).matches)
    reached = set(queue)
    while queue:
        for step in service.neighbours(version, queue.popleft(), facts):
            if step.status == "followable" and step.node.node_id not in reached:
                reached.add(step.node.node_id)
                queue.append(step.node.node_id)
    return reached


UC_DEMO = [
    Fact(kind="finding", name="Bloody diarrhoea"),
    Fact(kind="test", name="haemoglobin", value=102, unit="g/L"),
    Fact(kind="test", name="faecal calprotectin", value=850, unit="ug/g"),
    Fact(kind="finding", name="stool frequency", value=8, unit="per day"),
    Fact(kind="test", name="stool culture", value="negative"),
    Fact(kind="test", name="colonoscopy with biopsy", value="ulcerative colitis"),
    Fact(kind="test", name="disease extent", value="E3"),
    Fact(kind="test", name="Truelove and Witts severity", value="severe"),
]


@pytest.fixture
def ibd(service: KnowledgeService) -> PackVersionRef:
    return service.load_pack(IBD)


def test_both_packs_validate(capsys: pytest.CaptureFixture[str]) -> None:
    assert validate_main([str(IBD), str(URO)]) == 0
    out = capsys.readouterr().out
    assert "OK" in out and "pack IBD v1.1" in out and "pack URO v0.1" in out
    assert validate_main([str(IBD), str(IBD)]) == 1
    assert validate_main([str(FIXTURES / "email.yaml")]) == 1
    assert validate_main([]) == 2


def test_uc_demo_reaches_pancolitis_severe_and_tier_2(
    service: KnowledgeService, ibd: PackVersionRef
) -> None:
    entries = {n.node_id for n in service.search(ibd, UC_DEMO).matches}
    assert entries == {"IBD-N1", "IBD-N3", "IBD-N5", "IBD-N6"}
    reached = _walk(service, ibd, UC_DEMO)
    assert {"IBD-N10", "IBD-N11", "IBD-N32", "IBD-N34", "IBD-N41"} <= reached
    assert {"IBD-N51", "IBD-N52"} <= reached  # Tier 2 drug options
    assert "IBD-N40" not in reached and "IBD-N12" not in reached
    escalation = service.neighbours(ibd, "IBD-N41", UC_DEMO, "escalate_to")
    assert {s.status for s in escalation} == {"not_taken", "unknown_input"}  # 8 stools; no CRP
    tier = service.get_node(ibd, "IBD-N41")
    assert tier.fields["tier"] == 2 and tier.source_ids


def test_crohns_demo_reaches_a_subtype(service: KnowledgeService, ibd: PackVersionRef) -> None:
    facts = [
        Fact(kind="finding", name="abdominal pain"),
        Fact(kind="test", name="calprotectin", value=600, unit="mg/kg"),
        Fact(kind="test", name="colonoscopy", value="Crohn's disease"),
        Fact(kind="test", name="crohn's location", value="L1"),
        Fact(kind="test", name="crohn's activity", value="moderate"),
    ]
    reached = _walk(service, ibd, facts)
    assert {"IBD-N12", "IBD-N35", "IBD-N43", "IBD-N55"} <= reached
    assert not {"IBD-N11", "IBD-N36", "IBD-N37"} & reached


def test_infectious_colitis_alternative_present(
    service: KnowledgeService, ibd: PackVersionRef
) -> None:
    steps = service.neighbours(ibd, "IBD-N10", UC_DEMO)
    alternative = [s for s in steps if s.status == "alternative"]
    assert [s.node.node_id for s in alternative] == ["IBD-N13"]
    assert alternative[0].node.alternative is True
    assert alternative[0].edge.relation == "alternative_to"
    tests = [s.node.node_id for s in service.neighbours(ibd, "IBD-N13", [])]
    assert tests == ["IBD-N20"]


def test_urology_walk_reaches_its_plan(service: KnowledgeService) -> None:
    uro = service.load_pack(URO)
    facts = [
        Fact(kind="finding", name="loin to groin pain"),
        Fact(kind="test", name="CT KUB", value="ureteric stone"),
        Fact(kind="test", name="stone size", value="0.6", unit="cm"),
    ]
    reached = _walk(service, uro, facts)
    assert {"URO-N1", "URO-N2", "URO-N5", "URO-N6"} <= reached
    graph = service.subgraph(uro, sorted(reached))
    assert graph.missing == [] and all(n.source_ids for n in graph.nodes)


def _check_copy() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_copy", PROJECT_ROOT / "scripts" / "check_copy.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_copy_flags_26_word_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    check_copy = _check_copy()
    passage_words = [f"word{i}" for i in range(60)]
    passage = " ".join(passage_words)
    copied_26 = "Intro " + " ".join(passage_words[10:36]) + ", then mine."
    copied_25 = "Intro " + " ".join(passage_words[10:35]) + ", then mine."
    runs = check_copy.find_copied_runs(copied_26, passage)
    assert len(runs) == 1 and len(runs[0].split()) == 26
    assert check_copy.find_copied_runs(copied_25, passage) == []
    passages = tmp_path / "passages"
    passages.mkdir()
    (passages / "TST-S1.txt").write_text(passage, encoding="utf-8")
    pack = tmp_path / "pack.yaml"
    pack.write_text(
        (FIXTURES / "minimal.yaml")
        .read_text(encoding="utf-8")
        .replace("Diarrhoea with visible blood.", copied_26),
        encoding="utf-8",
    )
    assert check_copy.main([str(pack), "--passages", str(passages)]) == 1
    assert "FLAG" in capsys.readouterr().out
    assert check_copy.main([str(IBD), "--passages", str(passages)]) == 0
    assert check_copy.main([str(IBD), "--passages", str(tmp_path / "none")]) == 2


def test_uc_after_anti_tnf_failure_reaches_the_class_switch(
    service: KnowledgeService, ibd: PackVersionRef
) -> None:
    # Day-3 CRP above 45 mg/L escalates to Tier 3, where the history edges start.
    no_response = [*UC_DEMO, Fact(kind="finding", name="CRP", value=50, unit="mg/L")]
    assert "IBD-N42" in _walk(service, ibd, no_response)
    assert "IBD-N46" not in _walk(service, ibd, no_response)  # no history: not taken
    history = [
        Fact(kind="therapy", name="remicade", value="failed"),
        Fact(kind="therapy", name="corticosteroid", value="responded"),
    ]
    reached = _walk(service, ibd, [*no_response, *history])
    assert {"IBD-N46", "IBD-N54", "IBD-N57", "IBD-N58", "IBD-N72", "IBD-N102"} <= reached
    assert "IBD-N99" not in reached
    refractory = [Fact(kind="therapy", name="corticosteroid", value="failed"), history[0]]
    assert "IBD-N99" in _walk(service, ibd, [*no_response, *refractory])


def test_day3_criteria_link_to_the_tier_their_threshold_escalates_to(
    service: KnowledgeService, ibd: PackVersionRef
) -> None:
    assert [n.node_id for n in service.criterion_targets(ibd, "IBD-N80")] == ["IBD-N42"]
    assert [n.node_id for n in service.criterion_targets(ibd, "IBD-N81")] == ["IBD-N42"]


def test_measurements_watchouts_and_unwired_criteria_link_nowhere(
    service: KnowledgeService, ibd: PackVersionRef
) -> None:
    assert service.criterion_targets(ibd, "IBD-N70") == []  # monitoring, not a decision
    assert service.criterion_targets(ibd, "IBD-N90") == []  # watch-out, prose only
    assert service.criterion_targets(ibd, "IBD-N82") == []  # no wired consequence
    assert service.criterion_targets(ibd, "IBD-N51") == []  # not a criterion


def test_evaluate_criterion_checks_the_value_against_the_wired_edge(
    service: KnowledgeService, ibd: PackVersionRef
) -> None:
    met, targets = service.evaluate_criterion(ibd, "IBD-N81", 60)
    assert met is True
    assert [n.node_id for n in targets] == ["IBD-N42"]
    assert service.evaluate_criterion(ibd, "IBD-N81", 20) == (False, [])
    assert service.evaluate_criterion(ibd, "IBD-N90", 1) == (False, [])
