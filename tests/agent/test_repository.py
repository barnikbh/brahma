"""``WalkRepository`` (plan Step 6; FR5.9, FR4.7, NFR8.3)."""

from __future__ import annotations

import sqlite3

import pytest

from brahma.agent.models import EmittedLine, ExploreLane, SectionState, Walk
from brahma.agent.repository import WalkRepository
from brahma.cases import Case
from brahma.knowledge import PackVersionRef


def _walk(case_id: str, walk_id: str = "wk-1", started: str = "2026-10-30T10:00:00") -> Walk:
    return Walk(
        walk_id=walk_id,
        case_id=case_id,
        profile_id="p-maya",
        pack_version=PackVersionRef(pack="IBD", number="1.0"),
        provider="recorded",
        model="recorded",
        started_at=started,
    )


def _lane(walk_id: str, lane_id: str = "ln-1", branch: str = "IBD-N13") -> ExploreLane:
    return ExploreLane(
        lane_id=lane_id,
        walk_id=walk_id,
        branch_node_id=branch,
        node_ids=[branch, "IBD-N20"],
        created_at="2026-10-30T10:05:00",
    )


def test_a_walk_round_trips(repo: WalkRepository, demo_case: Case) -> None:
    walk = _walk(demo_case.case_id)
    walk.findings = [{"name": "Hb", "value": 10.2, "unit": "g/dL"}]
    walk.answers = {"IBD-N21": "ulcerative colitis"}
    repo.create(walk)
    assert repo.get("wk-1") == walk
    assert repo.get("wk-missing") is None


def test_progress_is_saved_so_a_walk_resumes_after_the_last_section(
    repo: WalkRepository, demo_case: Case
) -> None:
    walk = _walk(demo_case.case_id)
    repo.create(walk)
    line = EmittedLine(section_id="findings", text="t", node_ids=["IBD-N1"])
    walk.replace_section(walk.section("findings"))
    walk.replace_section(SectionState(section_id="findings", lines=[line], done=True))
    walk.last_section_done = 0
    walk.status = "error"
    repo.save_progress(walk)
    stored = repo.get("wk-1")
    assert stored is not None
    assert (stored.status, stored.last_section_done) == ("error", 0)
    assert stored.sections[0].lines == [line]


def test_saving_an_unknown_walk_fails_loudly(repo: WalkRepository, demo_case: Case) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_progress(_walk(demo_case.case_id, "wk-never-created"))


def test_latest_walk_per_case(repo: WalkRepository, demo_case: Case) -> None:
    assert repo.latest_for_case(demo_case.case_id) is None
    repo.create(_walk(demo_case.case_id, "wk-1", "2026-10-30T10:00:00"))
    repo.create(_walk(demo_case.case_id, "wk-2", "2026-10-30T11:00:00"))
    latest = repo.latest_for_case(demo_case.case_id)
    assert latest is not None and latest.walk_id == "wk-2"


def test_lanes_stay_separate_per_walk_and_one_open_per_branch(
    repo: WalkRepository, demo_case: Case
) -> None:
    repo.create(_walk(demo_case.case_id, "wk-1"))
    repo.create(_walk(demo_case.case_id, "wk-2", "2026-10-30T11:00:00"))
    repo.add_lane(_lane("wk-1"))
    repo.add_lane(_lane("wk-2", "ln-2"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_lane(_lane("wk-1", "ln-3"))
    assert [lane.lane_id for lane in repo.lanes_for_walk("wk-1")] == ["ln-1"]
    lane = repo.open_lane("wk-1", "IBD-N13")
    assert lane is not None
    lane.status = "stopped"
    repo.save_lane(lane)
    assert repo.open_lane("wk-1", "IBD-N13") is None
    assert repo.open_lane("wk-2", "IBD-N13") is not None
    repo.add_lane(_lane("wk-1", "ln-4"))  # a stopped lane frees the branch
    assert len(repo.lanes_for_walk("wk-1")) == 2
