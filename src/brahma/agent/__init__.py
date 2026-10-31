"""Brahma grounded agent (U4): the grounding guard and the deterministic graph walk.

Decision support, not diagnosis. The public interface is contract C6: ``Guard``
(``check_line``, ``check_line_by_source``) and ``WalkEngine`` (``run_walk`` and the
streamed walk), plus the models and typed errors below. The walk chooses nodes only by
searching and traversing the knowledge graph; the model writes text from those nodes,
and no line is shown unless the guard passed it.
"""

from brahma.agent.db import ag_connect, ensure_ag_schema
from brahma.agent.engine import WalkEngine
from brahma.agent.errors import (
    AgentError,
    ExploreInvalid,
    FindingsNotReady,
    GuardFailed,
    WalkNotFound,
    WalkNotResumable,
    WalkRequestInvalid,
)
from brahma.agent.guard import Guard
from brahma.agent.logging import WalkLogger
from brahma.agent.models import (
    DISCLAIMER,
    SECTION_ORDER,
    CheckResult,
    ExploreLane,
    GuardFailure,
    MapData,
    Walk,
    WalkEvent,
    WalkRequest,
    WalkResult,
)
from brahma.agent.repository import WalkRepository
from brahma.knowledge.models import Claim

__all__ = [
    "DISCLAIMER",
    "SECTION_ORDER",
    "AgentError",
    "CheckResult",
    "Claim",
    "ExploreInvalid",
    "ExploreLane",
    "FindingsNotReady",
    "Guard",
    "GuardFailed",
    "GuardFailure",
    "MapData",
    "Walk",
    "WalkEngine",
    "WalkEvent",
    "WalkLogger",
    "WalkNotFound",
    "WalkNotResumable",
    "WalkRepository",
    "WalkRequest",
    "WalkRequestInvalid",
    "WalkResult",
    "ag_connect",
    "ensure_ag_schema",
]
