"""Pydantic models for the grounded agent (entities.md, contracts C6 and C8).

Python attributes are snake_case; the contract names are camelCase aliases (``walkId``,
``nodeIds``). Value objects are immutable; ``Walk`` and ``ExploreLane`` are the two stored
entities and change as a walk runs, so they are mutable. Every model refuses unknown keys.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from brahma.knowledge.models import Claim, PackVersionRef, TherapyResponse

DISCLAIMER = "Decision support, not diagnosis"
MAX_TEXT_LENGTH = 4000
MAX_LINE_LENGTH = 1000

SectionId = Literal[
    "findings", "diagnosis", "tests", "subtype", "treatment", "monitor", "diet", "watch_outs"
]
# FR4.6: findings -> working diagnosis -> confirm and refine -> refined sub-type ->
# treatment tiers (entry marked) -> monitor -> diet -> watch-outs and surgery triggers.
SECTION_ORDER: tuple[SectionId, ...] = (
    "findings",
    "diagnosis",
    "tests",
    "subtype",
    "treatment",
    "monitor",
    "diet",
    "watch_outs",
)
# Fixed section headers: they are not model text and are not checked (BR1.3).
SECTION_TITLES: dict[str, str] = {
    "findings": "Findings",
    "diagnosis": "Working diagnosis",
    "tests": "Confirm and refine",
    "subtype": "Refined sub-type",
    "treatment": "Treatment tiers",
    "monitor": "Monitor",
    "diet": "Diet",
    "watch_outs": "Watch-outs and surgery triggers",
    "why": "Why",
    "explore": "Exploring",
}
WHY_SECTION = "why"
EXPLORE_SECTION = "explore"
WHY_INDEX = len(SECTION_ORDER)

WalkStatus = Literal["paused", "answered", "needs_data", "out_of_knowledge", "error"]
# ``follow_up``: a turn after an ended walk that adds treatment history (no forms).
WalkKind = Literal["walk", "follow_up", "review"]
Outcome = Literal["answered", "needs_data", "out_of_knowledge", "error"]
WalkMode = Literal["start", "continue", "rewalk", "explore", "stop_explore", "follow_up", "review"]
FormKind = Literal["confirm-findings", "needs-data", "edit-treatment", "patient-details"]
LaneStatus = Literal["open", "stopped"]
EventType = Literal[
    "progress",
    "form",
    "paused",
    "map_update",
    "line",
    "section_done",
    "done",
    "error",
    "lane_closed",
    "history",
    "reviewed",
]
# C8: progress.step is a fixed label and never carries model text.
ProgressStep = Literal[
    "reading_findings",
    "matching_diagnosis",
    "refining",
    "planning_treatment",
    "checking_sources",
    "writing_explanation",
]
MapStatus = Literal[
    "used",
    "entry",
    "test_needed",
    "not_in_pack",
    "bypassed",
    "not_taken",
    "exploring",
    "tried",
    "option",
    "planned",
    "chosen",
    # Care-loop statuses, set by the frontier from the case's events.
    "now",
    "todo_first",
    "due",
    "watch",
    "present",
    "done",
]
CareEventKind = Literal["present", "result", "done"]
EdgeStyle = Literal["walked", "bypassed", "not_taken", "exploring"]


class AgModel(BaseModel):
    """Base value object: camelCase aliases, snake_case attributes, unknown keys refused."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        frozen=True,
    )


class AgEntity(AgModel):
    """Base stored entity: like ``AgModel`` but mutable while a walk runs."""

    model_config = ConfigDict(frozen=False, validate_assignment=True)


# --- Guard (C6) ------------------------------------------------------------------------


class GuardFailure(AgModel):
    """Why a line failed: a claim that matched no cited node, or a citation problem."""

    claim: Claim | None = None
    reason: str
    node_id: str | None = None


class CheckResult(AgModel):
    """The result of ``check_line`` or ``check_line_by_source`` (C6).

    ``error`` holds the exception class when the guard itself failed (NFR8.5); the line
    then counts as failed.
    """

    passed: bool
    claims: list[Claim]
    failures: list[GuardFailure]
    error: str | None = None


# --- Model output ----------------------------------------------------------------------


class ExtractedFinding(AgModel):
    """One finding chip as the model extracted it from the doctor's text (BR2.1)."""

    kind: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    value: float | str | None = None
    unit: str | None = None
    duration: str | None = None


class ExtractOutput(AgModel):
    """The structured reply for purpose ``extract``."""

    findings: list[ExtractedFinding]


class TherapyItem(AgModel):
    """One past therapy as the model read it from a follow-up message."""

    drug: str = Field(min_length=1, max_length=120)
    response: TherapyResponse


class TreatmentHistoryOutput(AgModel):
    """The structured reply for purpose ``treatment_history``."""

    therapies: list[TherapyItem]


class DraftLine(AgModel):
    """One line the model wrote, with the nodes it cites and the claims it declares."""

    text: str = Field(min_length=1, max_length=MAX_LINE_LENGTH)
    node_ids: list[str]
    claims: list[Claim] = Field(default_factory=list)


class DraftOutput(AgModel):
    """The structured reply for purposes ``write_section`` and ``why``."""

    lines: list[DraftLine]


# --- Walk state ------------------------------------------------------------------------


class EmittedLine(AgModel):
    """A line that passed the guard and was sent (C8 ``line`` event)."""

    section_id: str
    text: str
    node_ids: list[str]
    lane_id: str | None = None


class SectionState(AgModel):
    """The lines sent for one section and how many were rejected."""

    section_id: str
    lines: list[EmittedLine] = Field(default_factory=list)
    rejected: int = 0
    done: bool = False


class WalkCounts(AgModel):
    """Summary counts: walked steps, cited lines and ungrounded (rejected) lines (FR4.3)."""

    steps: int = 0
    cited: int = 0
    ungrounded: int = 0


class Walk(AgEntity):
    """One walk of a case's findings through the graph (entities.md). Resumable (FR5.9)."""

    walk_id: str
    case_id: str
    profile_id: str
    kind: WalkKind = "walk"
    pack_version: PackVersionRef | None = None
    live_version_at_start: str | None = None
    previous_pack_version: str | None = None
    status: WalkStatus = "paused"
    waiting_for: str | None = None
    waiting_kind: FormKind | None = None
    text: str = ""
    findings: list[dict[str, Any]] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    asked_test_ids: list[str] = Field(default_factory=list)
    # Follow-up only: the past therapies, {drug, response, nodeIds}; None until read.
    history: list[dict[str, Any]] | None = None
    base_history: list[dict[str, Any]] = Field(default_factory=list)
    path_node_ids: list[str] = Field(default_factory=list)
    sections: list[SectionState] = Field(default_factory=list)
    last_section_done: int | None = None
    counts: WalkCounts = Field(default_factory=WalkCounts)
    provider: str
    model: str
    queued_message_ids: list[str] = Field(default_factory=list)
    map: dict[str, Any] | None = None
    session_id: str | None = None
    started_at: str
    ended_at: str | None = None

    def section(self, section_id: str) -> SectionState:
        """The stored state of a section, creating an empty one when it is new."""
        for state in self.sections:
            if state.section_id == section_id:
                return state
        state = SectionState(section_id=section_id)
        self.sections = [*self.sections, state]
        return state

    def replace_section(self, state: SectionState) -> None:
        """Store a section's new state (states are immutable value objects)."""
        self.sections = [state if s.section_id == state.section_id else s for s in self.sections]

    def recount(self) -> None:
        """Derive cited and ungrounded from the sections, so a retry never counts twice."""
        self.counts = WalkCounts(
            steps=len(self.path_node_ids),
            cited=sum(len(s.lines) for s in self.sections),
            ungrounded=sum(s.rejected for s in self.sections),
        )


class TraverseChoice(AgEntity):
    """A doctor's chosen drug for one tier of a walk. Rows are append-only; the latest
    choice per walk and tier wins, so re-choosing never rewrites history."""

    choice_id: str
    walk_id: str
    tier_id: str
    node_id: str
    profile_id: str
    created_at: str


class CareEvent(AgEntity):
    """One thing that happened in the case, in order: a sign present now, a test or
    measurement result, or an action done. ``for_node_id`` scopes it to the action it
    was done for (a prerequisite result counts for that action); events are append-only."""

    event_id: str
    case_id: str
    kind: CareEventKind
    node_id: str
    value: str | None = None
    for_node_id: str | None = None
    profile_id: str
    created_at: str


class ExploreLane(AgEntity):
    """An explored alternative branch, kept apart from the main sections (FR4.7)."""

    lane_id: str
    walk_id: str
    branch_node_id: str
    node_ids: list[str]
    lines: list[EmittedLine] = Field(default_factory=list)
    rejected: int = 0
    status: LaneStatus = "open"
    created_at: str
    stopped_at: str | None = None


# --- Requests, events and results ------------------------------------------------------


class WalkRequest(AgModel):
    """The C8 walk request body (R-02). Text is limited to 4,000 characters (NFR8.1)."""

    mode: WalkMode
    text: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    form_message_id: str | None = None
    form_values: dict[str, Any] | None = None
    branch_node_id: str | None = None
    walk_id: str | None = None
    review_value: str | None = None


class FormField(AgModel):
    """One field of a confirm-findings or needs-data form."""

    name: str
    label: str
    kind: Literal["finding", "test_result"]
    finding_kind: str | None = None
    value: float | str | None = None
    unit: str | None = None
    duration: str | None = None
    node_id: str | None = None
    options: list[str] | None = None
    validation_state: str | None = None


class WalkEvent(AgModel):
    """One Server-Sent Event of the walk stream (C8)."""

    type: EventType
    payload: dict[str, Any]

    def sse(self) -> str:
        """The event in ``text/event-stream`` framing."""
        data = json.dumps(self.payload, ensure_ascii=False, separators=(",", ":"))
        return f"event: {self.type}\ndata: {data}\n\n"


class WalkResult(AgModel):
    """The result of ``run_walk`` (C6), for U7's benchmark."""

    walk_id: str
    outcome: Outcome
    sections: list[dict[str, Any]]
    counts: WalkCounts
    path_node_ids: list[str]
    pack_version: str | None = None


# --- Map (C8 R-02) ---------------------------------------------------------------------


class MapNode(AgModel):
    """One node on the map with its column and walk status."""

    node_id: str
    type: str
    label: str
    column: str
    status: MapStatus
    result: dict[str, Any] | None = None
    kind: str = "observation"
    pos: list[int] | None = None
    # Why a care-loop status lit this node, e.g. "Needed before Infliximab 5 mg/kg IV".
    reason: str | None = None


class MapEdge(AgModel):
    """One edge on the map with its style."""

    edge_id: str
    from_: str = Field(alias="from")
    to: str
    style: EdgeStyle
    relation: str | None = None


class PathItem(AgModel):
    """One node on the chosen path: drug, tier, review, monitor or watch-out."""

    node_id: str
    label: str
    type: str


class TraversePath(AgModel):
    """The chosen path's next steps. Labels come from the walked graph only."""

    drug: PathItem
    tier: PathItem
    requires: list[PathItem] = Field(default_factory=list)
    review: list[PathItem] = Field(default_factory=list)
    monitor: list[PathItem] = Field(default_factory=list)
    watch_outs: list[PathItem] = Field(default_factory=list)
    next_tiers: list[PathItem] = Field(default_factory=list)


class MapLane(AgModel):
    """An explore lane on the map."""

    lane_id: str
    node_ids: list[str]


class TimelineItem(AgModel):
    """One step of the case so far, for the strip under the map."""

    node_id: str
    label: str
    kind: str
    value: str | None = None
    at: str


class MapData(AgModel):
    """Map data for a walk or a replayed session."""

    version: str
    nodes: list[MapNode]
    edges: list[MapEdge]
    selected_path: list[str]
    explore_lanes: list[MapLane] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)


def version_label(version: PackVersionRef | None) -> str | None:
    """``"IBD 1.0"`` for a version, as stored in the audit and session records."""
    return f"{version.pack} {version.number}" if version is not None else None
