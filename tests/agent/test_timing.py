"""Local timing checks (NFR1.2, NFR1.4). Marked ``timing``: CI skips them."""

from __future__ import annotations

import time

import pytest

from brahma.agent.engine import WalkEngine
from brahma.agent.guard import Guard
from brahma.agent.models import WalkRequest
from brahma.cases import Case, CaseService
from brahma.knowledge import KnowledgeService, PackVersionRef
from tests.agent.conftest import DEMO_TEXT, DOCTOR

pytestmark = pytest.mark.timing


def test_first_progress_event_comes_within_3_seconds(engine: WalkEngine, demo_case: Case) -> None:
    started = time.perf_counter()
    events = engine.events(demo_case.case_id, WalkRequest(mode="start", text=DEMO_TEXT), DOCTOR)
    first = next(events)
    assert first.type == "progress"
    assert time.perf_counter() - started < 3.0
    list(events)


def test_a_line_check_takes_under_50_ms_once_the_vocabulary_is_cached(
    knowledge: KnowledgeService, cases: CaseService, demo_case: Case
) -> None:
    guard = Guard(knowledge, cases)
    version = PackVersionRef(pack="IBD", number="1.1")
    text = "Hydrocortisone 100 mg intravenously four times daily."
    guard.check_line(text, ["IBD-N51"], version, demo_case.case_id)
    started = time.perf_counter()
    for _ in range(20):
        assert guard.check_line(text, ["IBD-N51"], version, demo_case.case_id).passed
    assert (time.perf_counter() - started) / 20 < 0.05
