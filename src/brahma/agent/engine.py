"""``WalkEngine``: the grounded walk as a stream of events (C6, C8, BR2-BR4, FR4, FR5.9).

``events`` is a synchronous generator of ``WalkEvent``; ``stream`` runs it in a worker
thread so the server can send Server-Sent Events, and ``run_walk`` drives it without
SSE for U7. The flow (contract C8 "Walk event flow"):

- ``start``: extract findings (C4 ``extract``), validate them (C5 ``set_findings``),
  post a confirm-findings form, pause.
- ``continue``: apply the form, choose and pin the version, walk the graph
  deterministically, then either post a needs-data form and pause, or write each section
  from its walked nodes (C4 ``write_section``), check every line (Guard), write the why
  (C4 ``why``), record the session (C2) and end with ``done``.
- ``rewalk``: a new walk on the case's findings, re-pinned to a newer live version.
- ``explore`` / ``stop_explore``: a separate lane that never changes the main sections.
- ``follow_up``: chat text after a walk has ended. The model reads the treatment
  history (C4 ``treatment_history``); each drug is checked against the pack's drug
  nodes and a fixed confirmation line is posted. The graph is walked again with the
  history as ``therapy`` facts, and only the treatment, monitor and watch-out sections
  the history leads to are written, every line through the guard. When the history
  leads nowhere in the graph the answer is "No grounded answer".

A line is sent only after the guard passed it. A rejected line is written to the audit
as ``line_rejected`` and counted as ungrounded. On a model or guard failure the walk is
saved as ``error`` with everything done so far; ``continue`` with the same walk resumes
after the last completed section, so no line is sent twice.
"""

from __future__ import annotations

import math
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import anyio.to_thread
from pydantic import ValidationError

from brahma.agent import views
from brahma.agent.errors import (
    AgentError,
    ExploreInvalid,
    FindingsNotReady,
    GuardFailed,
    TraverseInvalid,
    WalkNotFound,
    WalkNotResumable,
    WalkRequestInvalid,
)
from brahma.agent.guard import Guard
from brahma.agent.logging import WalkLogger
from brahma.agent.models import (
    DISCLAIMER,
    EXPLORE_SECTION,
    SECTION_ORDER,
    SECTION_TITLES,
    WHY_INDEX,
    WHY_SECTION,
    DraftLine,
    EmittedLine,
    ExploreLane,
    FormField,
    FormKind,
    MapData,
    MapEdge,
    MapNode,
    Outcome,
    PathItem,
    ProgressStep,
    TraverseChoice,
    TraversePath,
    Walk,
    WalkEvent,
    WalkRequest,
    WalkResult,
    version_label,
)
from brahma.agent.repository import WalkRepository
from brahma.agent.traverse import Traversal, choose_version, lane_nodes, walk_graph
from brahma.agent.writer import Writer, node_payload
from brahma.cases.models import CaseStatus, DoseResult, FindingIn, MessageIn
from brahma.cases.service import CaseService
from brahma.knowledge.errors import NodeNotFound
from brahma.knowledge.models import Fact, Node, PackVersionRef
from brahma.knowledge.service import KnowledgeService
from brahma.platform.audit.models import AuditEntryIn, AuditKind, SessionRecordIn
from brahma.platform.audit.service import AuditService
from brahma.platform.base import new_id, utc_now
from brahma.platform.errors import (
    ModelAuthError,
    ModelError,
    ModelRateLimited,
    ModelTimeout,
)
from brahma.platform.models import ModelGateway
from brahma.platform.profiles import BENCHMARK_PROFILE_ID

NO_GROUNDED_ANSWER = "No grounded answer"
SUGGEST_BRANCH = "suggest_branch"
REVIEW_AND_REWALK = "review_findings_and_rewalk"
MAX_FORM_ROUNDS = 6
FIRST_STEP: dict[str, ProgressStep] = {
    "start": "reading_findings",
    "continue": "matching_diagnosis",
    "rewalk": "matching_diagnosis",
    "explore": "refining",
    "stop_explore": "refining",
    "follow_up": "reading_findings",
    "review": "reading_findings",
}
SECTION_STEP: dict[str, ProgressStep] = {
    "findings": "matching_diagnosis",
    "diagnosis": "matching_diagnosis",
    "tests": "refining",
    "subtype": "refining",
    "treatment": "planning_treatment",
    "monitor": "checking_sources",
    "diet": "checking_sources",
    "watch_outs": "checking_sources",
}
CASE_STATUS: dict[str, CaseStatus] = {
    "answered": "answered",
    "needs_data": "needs_data",
    "out_of_knowledge": "out_of_knowledge",
}
FINAL_OUTCOME: dict[str, Outcome] = {
    "answered": "answered",
    "needs_data": "needs_data",
    "out_of_knowledge": "out_of_knowledge",
}
MODEL_CODES: tuple[tuple[type[ModelError], str, str], ...] = (
    (ModelTimeout, "model_timeout", "The model provider did not answer in time."),
    (ModelRateLimited, "model_rate_limited", "The model provider is busy."),
    (ModelAuthError, "model_auth", "The model provider refused the configured key."),
)


def _event(event_type: str, /, **payload: Any) -> WalkEvent:
    return WalkEvent.model_validate({"type": event_type, "payload": payload})


def progress(step: ProgressStep) -> WalkEvent:
    """A ``progress`` event; its step is a fixed label, never model text (C8)."""
    return _event("progress", step=step)


def model_error_text(exc: ModelError) -> tuple[str, str]:
    """The event code and a plain message for a model failure (AC3.4.2)."""
    code, text = "model_unavailable", "The model provider gave no usable reply."
    for kind, known_code, known_text in MODEL_CODES:
        if isinstance(exc, kind):
            code, text = known_code, known_text
            break
    keep = " Your inputs are kept: select Retry." if exc.retryable else ""
    return code, text + keep


@dataclass
class _Ctx:
    """The walk a stream is working on, so a failure can be saved against it."""

    walk: Walk | None = None
    keep_walk: bool = False
    started: float = field(default_factory=time.perf_counter)


class WalkEngine:
    """Runs grounded walks over C1-C5 (see the module docstring)."""

    def __init__(
        self,
        *,
        knowledge: KnowledgeService,
        cases: CaseService,
        audit: AuditService,
        gateway: ModelGateway,
        repo: WalkRepository,
        logger: WalkLogger | None = None,
    ) -> None:
        self._knowledge = knowledge
        self._cases = cases
        self._audit = audit
        self._gateway = gateway
        self.repo = repo
        self.guard = Guard(knowledge, cases)
        self.writer = Writer(gateway)
        self.logger = logger or WalkLogger()

    # --- public interface --------------------------------------------------------------

    async def stream(
        self, case_id: str, request: WalkRequest, profile_id: str
    ) -> AsyncIterator[WalkEvent]:
        """The walk events, each produced in a worker thread (the gateway is synchronous)."""
        events = self.events(case_id, request, profile_id)
        while True:
            event = await anyio.to_thread.run_sync(next, events, None)
            if event is None:
                return
            yield event

    def events(self, case_id: str, request: WalkRequest, profile_id: str) -> Iterator[WalkEvent]:
        """The walk events for one request; failures end the stream with ``error``."""
        ctx = _Ctx(keep_walk=request.mode in ("explore", "stop_explore"))
        yield progress(FIRST_STEP[request.mode])
        try:
            self._cases.get_case(case_id)
            if request.mode == "start":
                yield from self._start(ctx, case_id, request, profile_id)
            elif request.mode == "continue":
                yield from self._continue(ctx, case_id, request)
            elif request.mode == "rewalk":
                yield from self._rewalk(ctx, case_id, profile_id)
            elif request.mode == "explore":
                yield from self._explore(ctx, case_id, request)
            elif request.mode == "follow_up":
                yield from self._follow_up(ctx, case_id, request, profile_id)
            elif request.mode == "review":
                yield from self._review(ctx, case_id, request, profile_id)
            else:
                yield from self._stop_explore(ctx, case_id, request)
        except ModelError as exc:
            code, message = model_error_text(exc)
            yield self._failed(ctx, code, message, exc.retryable, exc.log_label(), save=True)
        except GuardFailed as exc:
            yield self._failed(ctx, exc.code, str(exc), True, exc.log_label(), save=True)
        except AgentError as exc:
            yield self._failed(ctx, exc.code, str(exc), exc.retryable, exc.log_label(), save=False)
        except Exception as exc:  # the stream boundary: never end without an error event
            message = "Something went wrong. Your inputs are kept: select Retry."
            yield self._failed(ctx, "internal_error", message, True, type(exc).__name__, save=True)

    def run_walk(
        self,
        case_id: str,
        findings: list[FindingIn],
        answers: dict[str, str] | None = None,
        profile_id: str = BENCHMARK_PROFILE_ID,
    ) -> WalkResult:
        """A walk without SSE for U7: forms are answered from ``answers`` (W8, C6).

        ``answers`` maps a test node ID or test name to its result. Raises
        FindingsNotReady when a finding is invalid or in conflict.
        """
        validated = self._cases.set_findings(case_id, findings)
        if not self._cases.findings_ready(case_id):
            raise FindingsNotReady(case_id)
        walk = self._new_walk(case_id, profile_id, "; ".join(f.name for f in validated))
        walk.findings = [f.model_dump(by_alias=True) for f in validated]
        walk.answers = dict(answers or {})
        self.repo.create(walk)
        ctx = _Ctx(walk=walk)
        try:
            for _ in range(MAX_FORM_ROUNDS):
                if not any(e.type == "paused" for e in list(self._walk_on(walk))):
                    break
                self._cases.submit_form(case_id, str(walk.waiting_for))
                walk.waiting_for, walk.waiting_kind = None, None
        except (ModelError, AgentError) as exc:
            self._failed(ctx, "run_walk_failed", str(exc), False, type(exc).__name__, save=True)
        outcome: Outcome = FINAL_OUTCOME.get(walk.status, "error")
        return WalkResult(
            walk_id=walk.walk_id,
            outcome=outcome,
            sections=views.answer_sections(walk),
            counts=walk.counts,
            path_node_ids=walk.path_node_ids,
            pack_version=version_label(walk.pack_version),
        )

    def queue_message(self, case_id: str, message_id: str) -> list[str]:
        """Note free text sent during a walk (BR2.9); returns the offers to show now."""
        walk = self.repo.latest_for_case(case_id)
        if walk is None:
            return []
        if walk.status == "paused":
            walk.queued_message_ids = [*walk.queued_message_ids, message_id]
            self.repo.save_progress(walk)
            return []
        return [REVIEW_AND_REWALK]

    @staticmethod
    def can_follow_up(walk: Walk | None) -> bool:
        """Whether chat text now starts a follow-up turn: the walk ended with an answer
        (or needs data) on a pinned version, or was itself a follow-up."""
        if walk is None or walk.pack_version is None:
            return False
        if walk.status in ("answered", "needs_data"):
            return True
        return walk.kind == "follow_up" and walk.status == "out_of_knowledge"

    def map_data(self, case_id: str, walk_id: str | None = None) -> MapData | None:
        """The map of a walk (default: the case's latest) with its open explore lanes."""
        walk = self._load(case_id, walk_id) if walk_id else self.repo.latest_for_case(case_id)
        if walk is None or walk.map is None:
            return None
        base = MapData.model_validate(walk.map)
        lanes = self._open_lanes(walk)
        return views.with_lanes(base, lanes) if lanes else base

    def _open_lanes(self, walk: Walk) -> list[tuple[str, list[MapNode], list[MapEdge]]]:
        """The walk's open explore lanes as map fragments (empty when none)."""
        if walk.pack_version is None:
            return []
        return [
            (
                lane.lane_id,
                *views.lane_map(self._knowledge, walk.pack_version, lane.node_ids),
            )
            for lane in self.repo.lanes_for_walk(walk.walk_id)
            if lane.status == "open"
        ]

    def traverse_choice(
        self, case_id: str, node_id: str, profile_id: str
    ) -> tuple[MapData, str, TraversePath]:
        """Record the doctor's chosen drug option and re-light its tier's path.

        Deterministic: the walk is re-walked from its stored facts (no model call),
        prior choices are re-applied, and the map snapshot is rebuilt. Re-choosing
        another drug of the same tier moves the highlight; the audit keeps every event.
        The returned path is the tier's next steps, all taken from the walked graph.
        """
        walk = self.repo.latest_for_case(case_id)
        if walk is None:
            raise TraverseInvalid(node_id, "this case has no walk yet")
        if walk.status != "answered":
            raise TraverseInvalid(node_id, "the walk has not answered yet")
        if walk.pack_version is None or walk.map is None:
            raise TraverseInvalid(node_id, "the walk has no map yet")
        on_map = {n["nodeId"]: n["status"] for n in walk.map.get("nodes", [])}
        if on_map.get(node_id) != "option":
            raise TraverseInvalid(node_id, "not an option on this walk's map")
        version = walk.pack_version
        tier = next(
            (
                t
                for t, status in on_map.items()
                if status == "entry" and self._offers(version, t, node_id)
            ),
            None,
        )
        if tier is None:
            raise TraverseInvalid(node_id, "no entry tier offers this drug")
        previous = self.repo.choices_for_walk(walk.walk_id)
        facts = self._facts(walk, version)
        trav = walk_graph(self._knowledge, version, facts)
        trav.choices = {**previous, tier: node_id}
        label = str(walk.map.get("version") or "")
        data = views.build_map(self._knowledge, version, trav, label)
        path = self._traverse_path(version, trav, tier, node_id, facts)
        walk.map = data.model_dump(by_alias=True)
        self.repo.save_progress(walk)
        lanes = self._open_lanes(walk)
        data = views.with_lanes(data, lanes) if lanes else data
        self.repo.add_choice(
            TraverseChoice(
                choice_id=new_id("ch"),
                walk_id=walk.walk_id,
                tier_id=tier,
                node_id=node_id,
                profile_id=profile_id,
                created_at=utc_now(),
            )
        )
        self._append_audit(
            walk,
            "traverse_choice",
            {
                "walkId": walk.walk_id,
                "tierId": tier,
                "nodeId": node_id,
                "previousNodeId": previous.get(tier),
            },
        )
        drug = self._knowledge.get_node(version, node_id).label
        notice = f"{drug} chosen. Its tier's monitoring is now highlighted on the map."
        return data, notice, path

    def _traverse_path(
        self,
        version: PackVersionRef,
        trav: Traversal,
        tier_id: str,
        node_id: str,
        facts: list[Fact],
    ) -> TraversePath:
        """The tier's next steps for the card: review, monitor, watch-outs, next tiers."""
        review: list[PathItem] = []
        monitor: list[PathItem] = []
        watch_outs: list[PathItem] = []
        for member in trav.tier_downstream.get(tier_id, []):
            item = self._path_item(version, member)
            if item.type == "response_criterion":
                review.append(item)
            elif item.type == "monitoring":
                monitor.append(item)
            elif item.type in ("watch_out", "escalation"):
                watch_outs.append(item)
        next_tiers: list[PathItem] = []
        seen_tiers: set[str] = set()
        for step in self._knowledge.neighbours(version, tier_id, facts, "escalate_to"):
            if step.status != "not_taken" and step.node.node_id not in seen_tiers:
                seen_tiers.add(step.node.node_id)
                next_tiers.append(self._path_item(version, step.node.node_id))
        return TraversePath(
            drug=self._path_item(version, node_id),
            tier=self._path_item(version, tier_id),
            review=review,
            monitor=monitor,
            watch_outs=watch_outs,
            next_tiers=next_tiers,
        )

    def _path_item(self, version: PackVersionRef, node_id: str) -> PathItem:
        node = self._knowledge.get_node(version, node_id)
        return PathItem(node_id=node.node_id, label=node.label, type=node.type)

    def _offers(self, version: PackVersionRef, tier_id: str, node_id: str) -> bool:
        """Whether the tier offers the drug (relation match only; option status on the
        map already proved the edge was followable when the walk ran)."""
        return any(
            step.node.node_id == node_id
            for step in self._knowledge.neighbours(version, tier_id, [], "offers_drug")
        )

    # --- start and continue ------------------------------------------------------------

    def _new_walk(self, case_id: str, profile_id: str, text: str) -> Walk:
        current = self._gateway.current()
        case = self._cases.get_case(case_id)
        return Walk(
            walk_id=new_id("wk"),
            case_id=case_id,
            profile_id=profile_id,
            pack_version=case.pinned_pack_version,
            live_version_at_start=self._live_label(),
            text=text,
            provider=current.provider,
            model=current.model,
            started_at=utc_now(),
        )

    def _start(
        self, ctx: _Ctx, case_id: str, request: WalkRequest, profile_id: str
    ) -> Iterator[WalkEvent]:
        text = (request.text or "").strip()
        if not text:
            raise WalkRequestInvalid("a walk starts from the doctor's text")
        walk = self._new_walk(case_id, profile_id, text)
        self.repo.create(walk)
        ctx.walk = walk
        body = {"text": text, "walkId": walk.walk_id}
        self._cases.append_message(case_id, MessageIn(author="doctor", kind="text", body=body))
        self.logger.log(
            "walk_start",
            walkId=walk.walk_id,
            caseId=case_id,
            mode="start",
            provider=walk.provider,
            model=walk.model,
        )
        yield from self._extract(walk)

    def _extract(self, walk: Walk) -> Iterator[WalkEvent]:
        extracted = self.writer.extract(walk.text)
        items = [FindingIn.model_validate(f.model_dump()) for f in extracted]
        validated = self._cases.set_findings(walk.case_id, items)
        walk.findings = [f.model_dump(by_alias=True) for f in validated]
        yield from self._post_form(walk, "confirm-findings", views.finding_fields(validated))

    def _post_form(
        self, walk: Walk, kind: FormKind, fields: list[FormField]
    ) -> Iterator[WalkEvent]:
        dumped = [f.model_dump(by_alias=True) for f in fields]
        message = MessageIn(
            author="brahma",
            kind="form",
            form_kind=kind,
            body={"walkId": walk.walk_id, "fields": dumped},
        )
        message_id = self._cases.append_message(walk.case_id, message)
        walk.waiting_for, walk.waiting_kind, walk.status = message_id, kind, "paused"
        self.repo.save_progress(walk)
        yield _event("form", kind=kind, messageId=message_id, walkId=walk.walk_id, fields=dumped)
        yield _event("paused", walkId=walk.walk_id, waitingFor=message_id)

    def _load(self, case_id: str, walk_id: str | None) -> Walk:
        if not walk_id:
            raise WalkRequestInvalid("this step needs the walkId")
        walk = self.repo.get(walk_id)
        if walk is None or walk.case_id != case_id:
            raise WalkNotFound(walk_id)
        return walk

    def _continue(self, ctx: _Ctx, case_id: str, request: WalkRequest) -> Iterator[WalkEvent]:
        walk = self._load(case_id, request.walk_id)
        if walk.status not in ("paused", "error"):
            raise WalkNotResumable(walk.walk_id, f"the walk has ended ({walk.status})")
        ctx.walk = walk
        if walk.kind == "follow_up":
            yield from self._follow_on(walk)  # retry of a follow-up that failed
            return
        if request.form_message_id is not None:
            if request.form_message_id != walk.waiting_for:
                raise WalkNotResumable(walk.walk_id, "that is not the form this walk waits for")
            self._apply_form(walk, request.form_values or {})
        elif walk.waiting_for is not None:
            if walk.status == "paused":
                raise WalkNotResumable(walk.walk_id, "answer the open form first")
        elif not walk.findings:
            yield from self._extract(walk)  # retry of a start that failed while extracting
            return
        yield from self._walk_on(walk)

    def _apply_form(self, walk: Walk, values: dict[str, Any]) -> None:
        if walk.waiting_kind == "confirm-findings":
            raw = values.get("findings")
            if not isinstance(raw, list):
                raise WalkRequestInvalid("confirm-findings needs a findings list")
            try:
                items = [FindingIn.model_validate(item) for item in raw]
            except ValidationError:
                raise WalkRequestInvalid("a confirmed finding is not valid") from None
            validated = self._cases.set_findings(walk.case_id, items)
            walk.findings = [f.model_dump(by_alias=True) for f in validated]
            if not self._cases.findings_ready(walk.case_id):
                self.repo.save_progress(walk)
                raise FindingsNotReady(walk.case_id)
        else:
            answers = dict(walk.answers)
            for key, value in values.items():
                if isinstance(value, (str, int, float)) and str(value).strip():
                    answers[str(key)] = str(value).strip()
            walk.answers = answers
        form_id = str(walk.waiting_for)
        self._cases.submit_form(walk.case_id, form_id)
        body = {"walkId": walk.walk_id, "formMessageId": form_id, "values": values}
        self._cases.append_message(
            walk.case_id, MessageIn(author="doctor", kind="form_answer", body=body)
        )
        walk.waiting_for, walk.waiting_kind = None, None
        walk.status = "paused"
        self.repo.save_progress(walk)

    # --- the walk ----------------------------------------------------------------------

    def _facts(self, walk: Walk, version: PackVersionRef) -> list[Fact]:
        answers = views.answer_facts(self._knowledge, version, walk.answers)
        history = views.history_facts(walk.history or [])
        return [*views.finding_facts(walk.findings), *answers, *history]

    def _version_for(self, walk: Walk) -> PackVersionRef | None:
        """The walk's version; the first walk of a case chooses and pins it (BR2.7)."""
        if walk.pack_version is not None:
            return walk.pack_version
        case = self._cases.get_case(walk.case_id)
        facts = views.finding_facts(walk.findings)
        version = choose_version(self._knowledge, facts, case.pinned_pack_version)
        if version is not None:
            if case.pinned_pack_version != version:
                self._cases.pin(walk.case_id, version)
            walk.pack_version = version
        return version

    def _walk_on(self, walk: Walk) -> Iterator[WalkEvent]:
        version = self._version_for(walk)
        if version is None:
            trav = Traversal(version=None, outcome="out_of_knowledge")
        else:
            trav = walk_graph(self._knowledge, version, self._facts(walk, version))
        walk.path_node_ids = trav.path_node_ids
        label = version_label(version) or self._live_label()
        walk.map = (
            views.build_map(self._knowledge, version, trav, label).model_dump(by_alias=True)
            if version is not None and trav.outcome == "walked"
            else {"version": label, "nodes": [], "edges": [], "selectedPath": []}
        )
        walk.recount()
        yield _event(
            "map_update", walkId=walk.walk_id, nodes=walk.map["nodes"], edges=walk.map["edges"]
        )
        if trav.outcome == "out_of_knowledge" or version is None:
            yield from self._finish(walk, "out_of_knowledge")
            return
        new_tests = [t for t in trav.needed_tests if t not in walk.asked_test_ids]
        if new_tests:
            walk.asked_test_ids = [*walk.asked_test_ids, *new_tests]
            nodes = [self._knowledge.get_node(version, t) for t in new_tests]
            yield from self._post_form(walk, "needs-data", views.test_fields(nodes))
            return
        yield from self._write_sections(walk, version, trav)
        yield from self._write_why(walk, version, trav)
        yield from self._finish(walk, "needs_data" if trav.needed_tests else "answered")

    def _payloads(self, walk: Walk, nodes: list[Node], trav: Traversal) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for node in nodes:
            extra: dict[str, Any] = {}
            if node.node_id in trav.entry_tier_ids:
                extra["entryTier"] = True
            if node.type == "drug" and node.fields.get("doseBasis") in ("per_kg", "weight_band"):
                dose = self._cases.compute_dose(walk.case_id, node.node_id)
                extra["doseForThisPatient"] = views.dose_note(dose)
            payloads.append(self._one_band(walk.case_id, node_payload(node, extra)))
        return payloads

    def _one_band(self, case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Once the weight is known, the writer sees only this patient's dose of a weight-band
        drug: the guard grounds no other band, and no other band applies to this patient."""
        fields = payload["fields"]
        if fields.get("doseBasis") != "weight_band":
            return payload
        dose = self._cases.compute_dose(case_id, payload["nodeId"])
        if not isinstance(dose, DoseResult):
            return payload
        value = int(dose.value) if dose.value.is_integer() else dose.value
        only = {k: v for k, v in fields.items() if k != "doseBands"}
        return {**payload, "fields": {**only, "doseValue": value, "doseUnit": dose.unit}}

    def _write_sections(
        self,
        walk: Walk,
        version: PackVersionRef,
        trav: Traversal,
        plan: dict[str, list[str]] | None = None,
    ) -> Iterator[WalkEvent]:
        """Write each section of the walk, or only those of ``plan`` (a follow-up)."""
        context = views.case_context(self._cases.get_patient(walk.case_id))
        for index, section_id in enumerate(SECTION_ORDER):
            if walk.last_section_done is not None and index <= walk.last_section_done:
                continue
            node_ids = trav.section(section_id) if plan is None else list(plan.get(section_id, []))
            if node_ids:
                yield progress(SECTION_STEP[section_id])
                nodes = [self._knowledge.get_node(version, n) for n in node_ids]
                sources = views.sources_for(self._knowledge, version, nodes)
                drafts = self.writer.write_section(
                    section_id, self._payloads(walk, nodes, trav), sources, context
                )
                yield from self._emit(walk, version, section_id, drafts, node_ids)
                yield from self._section_done(walk, section_id, index, node_ids)
            else:
                walk.last_section_done = index

    def _write_why(
        self, walk: Walk, version: PackVersionRef, trav: Traversal
    ) -> Iterator[WalkEvent]:
        if walk.last_section_done is not None and walk.last_section_done >= WHY_INDEX:
            return
        yield progress("writing_explanation")
        node_ids = trav.path_node_ids
        nodes = [self._knowledge.get_node(version, n) for n in node_ids]
        context = views.case_context(self._cases.get_patient(walk.case_id))
        drafts = self.writer.why(
            self._payloads(walk, nodes, trav),
            views.sources_for(self._knowledge, version, nodes),
            context,
        )
        yield from self._emit(walk, version, WHY_SECTION, drafts, node_ids)
        yield from self._section_done(walk, WHY_SECTION, WHY_INDEX, node_ids)

    def _section_done(
        self, walk: Walk, section_id: str, index: int, node_ids: list[str]
    ) -> Iterator[WalkEvent]:
        state = walk.section(section_id)
        walk.replace_section(state.model_copy(update={"done": True}))
        walk.last_section_done = index
        walk.recount()
        self.repo.save_progress(walk)
        self.logger.log(
            "section_done",
            walkId=walk.walk_id,
            caseId=walk.case_id,
            sectionId=section_id,
            nodeIds=node_ids,
            lines=len(state.lines),
            rejected=state.rejected,
        )
        yield _event(
            "section_done",
            walkId=walk.walk_id,
            sectionId=section_id,
            title=SECTION_TITLES[section_id],
        )

    def _emit(
        self,
        walk: Walk,
        version: PackVersionRef,
        section_id: str,
        drafts: list[DraftLine],
        allowed: list[str],
    ) -> Iterator[WalkEvent]:
        """Send each draft line that passes the guard; reject and audit the rest (BR1.4)."""
        state = walk.section(section_id).model_copy(update={"rejected": 0})
        walk.replace_section(state)
        sent = {(line.text, tuple(line.node_ids)) for line in state.lines}
        for draft in drafts:
            key = (draft.text, tuple(draft.node_ids))
            if key in sent:
                continue  # already sent before a failure: never send a line twice (BR3.2)
            result = self.guard.check_line(
                draft.text,
                draft.node_ids,
                version,
                walk.case_id,
                declared=draft.claims,
                allowed_node_ids=allowed,
            )
            if result.passed:
                line = EmittedLine(section_id=section_id, text=draft.text, node_ids=draft.node_ids)
                state = state.model_copy(update={"lines": [*state.lines, line]})
                walk.replace_section(state)
                sent.add(key)
                yield _event("line", sectionId=section_id, text=line.text, nodeIds=line.node_ids)
                continue
            state = state.model_copy(update={"rejected": state.rejected + 1})
            walk.replace_section(state)
            self._reject(
                walk, section_id, draft, [f.model_dump(mode="json") for f in result.failures]
            )
            if result.error is not None:
                walk.recount()
                raise GuardFailed(result.error)

    def _reject(
        self,
        walk: Walk,
        section_id: str,
        draft: DraftLine,
        failures: list[dict[str, Any]],
        lane_id: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "walkId": walk.walk_id,
            "sectionId": section_id,
            "text": draft.text,
            "citedNodeIds": draft.node_ids,
            "failures": failures,
        }
        if lane_id is not None:
            payload["laneId"] = lane_id
        self._append_audit(walk, "line_rejected", payload)
        self.logger.log(
            "line_rejected",
            walkId=walk.walk_id,
            caseId=walk.case_id,
            sectionId=section_id,
            nodeIds=draft.node_ids,
            laneId=lane_id,
        )

    def _append_audit(self, walk: Walk, kind: AuditKind, payload: dict[str, Any]) -> str:
        return self._audit.append(
            AuditEntryIn(
                kind=kind,
                case_id=walk.case_id,
                profile_id=walk.profile_id,
                pack_version=version_label(walk.pack_version),
                provider=walk.provider,
                model=walk.model,
                benchmark_run_id=self._cases.get_case(walk.case_id).benchmark_run_id,
                payload=payload,
            )
        )

    def _finish(self, walk: Walk, outcome: Outcome) -> Iterator[WalkEvent]:
        """Record the session (BR4.5), set the case status and send ``done`` (BR4.6)."""
        walk.status = outcome
        walk.ended_at = utc_now()
        walk.recount()
        case = self._cases.get_case(walk.case_id)
        label = version_label(walk.pack_version) or self._live_label()
        sections = views.answer_sections(walk)
        summary = self._summary(walk, outcome)
        why = [s for s in sections if s["sectionId"] == WHY_SECTION]
        record = SessionRecordIn.model_validate(
            {
                "caseId": walk.case_id,
                "walkId": walk.walk_id,
                "profileId": walk.profile_id,
                "packVersion": label,
                "provider": walk.provider,
                "model": walk.model,
                "inputs": {
                    "text": walk.text,
                    "findings": walk.findings,
                    "history": walk.history or [],
                },
                "pathNodeIds": walk.path_node_ids,
                "answer": {
                    "summary": summary,
                    "sections": [s for s in sections if s["sectionId"] != WHY_SECTION],
                    "counts": walk.counts.model_dump(),
                },
                "sources": self._path_sources(walk),
                "explanation": why[0]["lines"] if why else [],
                "outcome": outcome,
                "benchmarkRunId": case.benchmark_run_id,
            }
        )
        walk.session_id = self._audit.record_session(record)
        body = {
            "walkId": walk.walk_id,
            "sessionId": walk.session_id,
            "outcome": outcome,
            "summary": summary,
            "sections": sections,
            "packVersion": label,
            "disclaimer": DISCLAIMER,
        }
        if walk.kind == "follow_up":
            body["history"] = walk.history or []
        self._cases.append_message(
            walk.case_id, MessageIn(author="brahma", kind="pathway", body=body)
        )
        # A follow-up with no grounded answer leaves the case's answer as it was.
        if outcome in CASE_STATUS and not (walk.kind == "follow_up" and outcome != "answered"):
            self._cases.set_status(walk.case_id, CASE_STATUS[outcome])
        self.repo.save_progress(walk)
        self.logger.log(
            "walk_done",
            walkId=walk.walk_id,
            caseId=walk.case_id,
            outcome=outcome,
            counts=walk.counts.model_dump(),
            pathNodeIds=walk.path_node_ids,
            packVersion=label,
            provider=walk.provider,
            model=walk.model,
        )
        yield _event("done", **self._done_payload(walk, outcome, label))

    def _done_payload(self, walk: Walk, outcome: Outcome, label: str) -> dict[str, Any]:
        offers = [REVIEW_AND_REWALK] if walk.queued_message_ids else []
        payload: dict[str, Any] = {
            "walkId": walk.walk_id,
            "sessionId": walk.session_id,
            "outcome": outcome,
            "counts": walk.counts.model_dump(),
            "packVersion": label,
            "provider": walk.provider,
            "model": walk.model,
            "disclaimer": DISCLAIMER,
        }
        if walk.previous_pack_version is not None:
            payload["previousPackVersion"] = walk.previous_pack_version
        payload["followUp"] = self.can_follow_up(walk)
        if outcome == "out_of_knowledge":
            payload["message"] = NO_GROUNDED_ANSWER
            offers = [SUGGEST_BRANCH, *offers]
        payload["offers"] = offers
        return payload

    def _summary(self, walk: Walk, outcome: Outcome) -> str:
        if outcome == "out_of_knowledge" or walk.pack_version is None:
            return NO_GROUNDED_ANSWER
        labels: list[str] = []
        for node_id in walk.path_node_ids:
            node = self._knowledge.get_node(walk.pack_version, node_id)
            if node.type in ("diagnosis", "subtype"):
                labels.append(node.label)
        if walk.kind == "follow_up":
            labels.extend(
                str(n["label"]) for n in (walk.map or {}).get("nodes", []) if n["status"] == "entry"
            )
        text = " → ".join(labels) or NO_GROUNDED_ANSWER
        if walk.previous_pack_version is not None:
            text += f" (re-walked on {version_label(walk.pack_version)}, was "
            text += f"{walk.previous_pack_version})"
        return text

    def _path_sources(self, walk: Walk) -> list[str]:
        if walk.pack_version is None:
            return []
        nodes = [self._knowledge.get_node(walk.pack_version, n) for n in walk.path_node_ids]
        return [s.source_id for s in views.sources_for(self._knowledge, walk.pack_version, nodes)]

    def _live_label(self) -> str:
        lives = sorted(self._knowledge.repo.live_versions(), key=lambda v: v.pack)
        return "; ".join(f"{v.pack} {v.number}" for v in lives) or "no pack loaded"

    def _failed(
        self, ctx: _Ctx, code: str, message: str, retryable: bool, error: str, *, save: bool
    ) -> WalkEvent:
        walk = ctx.walk
        if walk is not None and save and not ctx.keep_walk:
            walk.status = "error"
            walk.recount()
            self.repo.save_progress(walk)
        self.logger.log(
            "walk_error",
            walkId=walk.walk_id if walk else None,
            caseId=walk.case_id if walk else None,
            code=code,
            error=error,
            retryable=retryable,
            provider=self._gateway.current().provider,
        )
        return _event(
            "error",
            code=code,
            message=message,
            retryable=retryable,
            walkId=walk.walk_id if walk else None,
        )

    # --- follow-up turn (treatment history) ------------------------------------------

    def _follow_up(
        self, ctx: _Ctx, case_id: str, request: WalkRequest, profile_id: str
    ) -> Iterator[WalkEvent]:
        text = (request.text or "").strip()
        if not text:
            raise WalkRequestInvalid("a follow-up starts from the doctor's text")
        previous = self.repo.latest_for_case(case_id)
        if previous is None or not self.can_follow_up(previous):
            label = previous.walk_id if previous is not None else case_id
            raise WalkNotResumable(label, "a follow-up needs a walk that has ended")
        walk = self._new_walk(case_id, profile_id, text)
        walk.kind = "follow_up"
        walk.pack_version = previous.pack_version
        walk.findings = list(previous.findings)
        walk.answers = dict(previous.answers)
        walk.asked_test_ids = list(previous.asked_test_ids)
        if previous.kind in ("follow_up", "review"):
            walk.base_history = list(previous.history or [])
        self.repo.create(walk)
        ctx.walk = walk
        body = {"text": text, "walkId": walk.walk_id}
        self._cases.append_message(case_id, MessageIn(author="doctor", kind="text", body=body))
        self.logger.log(
            "walk_start",
            walkId=walk.walk_id,
            caseId=case_id,
            mode="follow_up",
            packVersion=version_label(walk.pack_version),
            provider=walk.provider,
            model=walk.model,
        )
        yield from self._follow_on(walk)

    def _follow_on(self, walk: Walk) -> Iterator[WalkEvent]:
        """Read the history (once), walk with it and write the sections it leads to."""
        version = walk.pack_version
        if version is None:
            raise WalkNotResumable(walk.walk_id, "a follow-up needs a pinned version")
        if walk.history is None:
            yield from self._read_history(walk, version)
        trav = walk_graph(self._knowledge, version, self._facts(walk, version))
        walk.path_node_ids = trav.path_node_ids
        label = version_label(version) or self._live_label()
        walk.map = views.build_map(self._knowledge, version, trav, label).model_dump(by_alias=True)
        walk.recount()
        yield _event(
            "map_update", walkId=walk.walk_id, nodes=walk.map["nodes"], edges=walk.map["edges"]
        )
        if trav.outcome != "walked" or not trav.history_tier_ids:
            yield from self._finish(walk, "out_of_knowledge")
            return
        yield from self._write_sections(walk, version, trav, trav.history_sections)
        yield from self._finish(walk, "answered")

    def _read_history(self, walk: Walk, version: PackVersionRef) -> Iterator[WalkEvent]:
        """Extract, check against the pack, confirm in chat and audit the history."""
        items = self.writer.treatment_history(walk.text)
        added, ignored = views.resolve_history(self._knowledge, version, items)
        walk.history = views.merge_history(walk.base_history, added)
        note = views.history_note(added, ignored, walk.text)
        body = {"text": note, "walkId": walk.walk_id, "history": added}
        self._cases.append_message(walk.case_id, MessageIn(author="brahma", kind="text", body=body))
        self._append_audit(
            walk,
            "treatment_history",
            {"walkId": walk.walk_id, "history": walk.history, "added": added, "ignored": ignored},
        )
        self.repo.save_progress(walk)
        yield _event("history", walkId=walk.walk_id, text=note, therapies=added)

    def _review(
        self, ctx: _Ctx, case_id: str, request: WalkRequest, profile_id: str
    ) -> Iterator[WalkEvent]:
        """Record a review result; walk the next tier when a criterion is met.

        The value becomes a review-scoped fact on a new walk, so presenting
        findings never re-tier. When the criterion is not met there is no new
        walk: the result is messaged and audited, and the tier stands.
        """
        node_id = (request.branch_node_id or "").strip()
        raw_value = (request.review_value or "").strip()
        if not node_id or not raw_value:
            raise WalkRequestInvalid("a review needs the criterion node and a value")
        try:
            value = float(raw_value)
        except ValueError:
            raise WalkRequestInvalid("a review result must be a number") from None
        if not math.isfinite(value) or value < 0:
            raise WalkRequestInvalid("a review result must be a number of 0 or more")
        previous = self.repo.latest_for_case(case_id)
        if previous is None or previous.status != "answered" or previous.pack_version is None:
            label = previous.walk_id if previous is not None else case_id
            raise WalkNotResumable(label, "a review needs an answered walk")
        version = previous.pack_version
        try:
            node = self._knowledge.get_node(version, node_id)
        except NodeNotFound:
            raise WalkRequestInvalid(f"unknown node {node_id}") from None
        if not self._knowledge.criterion_targets(version, node_id):
            raise WalkRequestInvalid(f"{node.label} has no wired next path")
        met, targets = self._knowledge.evaluate_criterion(version, node_id, value)
        measure = str(node.fields.get("measure"))
        unit = node.fields.get("unit")
        reading = f"{measure} {value:g}" + (f" {unit}" if unit else "")
        text = f"Review result: {reading}"
        if not met:
            self._cases.append_message(
                case_id,
                MessageIn(
                    author="doctor", kind="text", body={"text": text, "walkId": previous.walk_id}
                ),
            )
            self._append_audit(
                previous,
                "review_recorded",
                {
                    "walkId": previous.walk_id,
                    "nodeId": node_id,
                    "value": value,
                    "met": False,
                    "newWalkId": None,
                },
            )
            self.logger.log("review_recorded", walkId=previous.walk_id, caseId=case_id, met=False)
            yield _event(
                "reviewed",
                walkId=previous.walk_id,
                nodeId=node_id,
                met=False,
                text=(
                    f"Review recorded: {reading} does not meet {node.label}. "
                    "This result alone does not change the plan."
                ),
            )
            return
        walk = self._new_walk(case_id, profile_id, text)
        walk.kind = "review"
        walk.pack_version = previous.pack_version
        walk.findings = [
            *previous.findings,
            {
                "kind": "finding",
                "name": measure,
                "value": value,
                "unit": unit,
                "validationState": "ok",
                "context": "review",
            },
        ]
        walk.answers = dict(previous.answers)
        walk.asked_test_ids = list(previous.asked_test_ids)
        # Treatment history already given stays: a drug that failed must never be
        # suggested again because a day-3 result was recorded afterwards.
        if previous.history is not None:
            walk.history = list(previous.history)
            walk.base_history = list(previous.history)
        self.repo.create(walk)
        ctx.walk = walk
        self._cases.append_message(
            case_id,
            MessageIn(author="doctor", kind="text", body={"text": text, "walkId": walk.walk_id}),
        )
        tiers = ", ".join(t.label for t in targets)
        self._append_audit(
            walk,
            "review_recorded",
            {
                "walkId": walk.walk_id,
                "previousWalkId": previous.walk_id,
                "nodeId": node_id,
                "value": value,
                "met": True,
                "targetTierIds": [t.node_id for t in targets],
            },
        )
        self.logger.log("review_recorded", walkId=walk.walk_id, caseId=case_id, met=True)
        yield _event(
            "reviewed",
            walkId=walk.walk_id,
            nodeId=node_id,
            met=True,
            text=f"Review recorded: {reading} meets {node.label} — {tiers} is now the entry path.",
        )
        yield from self._walk_on(walk)

    # --- rewalk and explore ------------------------------------------------------------

    def _rewalk(self, ctx: _Ctx, case_id: str, profile_id: str) -> Iterator[WalkEvent]:
        previous = self.repo.latest_for_case(case_id)
        if previous is None:
            raise WalkNotFound(f"latest walk of {case_id}")
        findings = self._cases.list_findings(case_id)
        if not self._cases.findings_ready(case_id):
            raise FindingsNotReady(case_id)
        case = self._cases.get_case(case_id)
        newer = self._cases.newer_version(case_id)
        walk = self._new_walk(case_id, profile_id, previous.text)
        walk.findings = [f.model_dump(by_alias=True) for f in findings] or previous.findings
        walk.answers = dict(previous.answers)
        walk.asked_test_ids = list(previous.asked_test_ids)
        if newer is not None:
            walk.previous_pack_version = version_label(case.pinned_pack_version)
            self._cases.pin(case_id, newer)
            walk.pack_version = newer
        self.repo.create(walk)
        ctx.walk = walk
        self.logger.log(
            "walk_start",
            walkId=walk.walk_id,
            caseId=case_id,
            mode="rewalk",
            packVersion=version_label(walk.pack_version),
            provider=walk.provider,
        )
        yield from self._walk_on(walk)

    def _explore_target(
        self, walk: Walk, branch_node_id: str | None
    ) -> tuple[PackVersionRef, Node]:
        if not branch_node_id:
            raise WalkRequestInvalid("explore needs the branchNodeId")
        if walk.pack_version is None:
            raise ExploreInvalid(branch_node_id, "the walk has no pack version yet")
        try:
            node = self._knowledge.get_node(walk.pack_version, branch_node_id)
        except NodeNotFound:
            raise ExploreInvalid(branch_node_id, "not in this pack version") from None
        on_map = {n["nodeId"]: n["status"] for n in (walk.map or {}).get("nodes", [])}
        if not node.alternative and on_map.get(branch_node_id) != "not_taken":
            raise ExploreInvalid(branch_node_id, "not an alternative on this walk's map")
        return walk.pack_version, node

    def _explore(self, ctx: _Ctx, case_id: str, request: WalkRequest) -> Iterator[WalkEvent]:
        walk = self._load(case_id, request.walk_id)
        ctx.walk = walk
        version, branch = self._explore_target(walk, request.branch_node_id)
        if self.repo.open_lane(walk.walk_id, branch.node_id) is not None:
            raise ExploreInvalid(branch.node_id, "this branch is already being explored")
        node_ids = lane_nodes(self._knowledge, version, branch.node_id)
        lane = ExploreLane(
            lane_id=new_id("ln"),
            walk_id=walk.walk_id,
            branch_node_id=branch.node_id,
            node_ids=node_ids,
            created_at=utc_now(),
        )
        self.repo.add_lane(lane)
        self._append_audit(
            walk,
            "explore",
            {
                "walkId": walk.walk_id,
                "laneId": lane.lane_id,
                "branchNodeId": branch.node_id,
                "nodeIds": node_ids,
            },
        )
        nodes, edges = views.lane_map(self._knowledge, version, node_ids)
        yield _event(
            "map_update",
            walkId=walk.walk_id,
            laneId=lane.lane_id,
            nodes=[n.model_dump(by_alias=True) for n in nodes],
            edges=[e.model_dump(by_alias=True) for e in edges],
        )
        graph_nodes = [self._knowledge.get_node(version, n) for n in node_ids]
        drafts = self.writer.write_section(
            EXPLORE_SECTION,
            [self._one_band(case_id, node_payload(n)) for n in graph_nodes],
            views.sources_for(self._knowledge, version, graph_nodes),
            views.case_context(self._cases.get_patient(case_id)),
        )
        for draft in drafts:
            result = self.guard.check_line(
                draft.text,
                draft.node_ids,
                version,
                case_id,
                declared=draft.claims,
                allowed_node_ids=node_ids,
            )
            if result.passed:
                line = EmittedLine(
                    section_id=EXPLORE_SECTION,
                    text=draft.text,
                    node_ids=draft.node_ids,
                    lane_id=lane.lane_id,
                )
                lane.lines = [*lane.lines, line]
                yield _event(
                    "line",
                    sectionId=EXPLORE_SECTION,
                    laneId=lane.lane_id,
                    text=line.text,
                    nodeIds=line.node_ids,
                )
            else:
                lane.rejected += 1
                failures = [f.model_dump(mode="json") for f in result.failures]
                self._reject(walk, EXPLORE_SECTION, draft, failures, lane.lane_id)
                if result.error is not None:
                    self.repo.save_lane(lane)
                    raise GuardFailed(result.error)
        self.repo.save_lane(lane)
        yield _event(
            "section_done",
            walkId=walk.walk_id,
            sectionId=EXPLORE_SECTION,
            laneId=lane.lane_id,
            title=SECTION_TITLES[EXPLORE_SECTION],
        )

    def _stop_explore(self, ctx: _Ctx, case_id: str, request: WalkRequest) -> Iterator[WalkEvent]:
        walk = self._load(case_id, request.walk_id)
        ctx.walk = walk
        branch_id = request.branch_node_id
        if not branch_id:
            raise WalkRequestInvalid("stop_explore needs the branchNodeId")
        lane = self.repo.open_lane(walk.walk_id, branch_id)
        if lane is None:
            raise ExploreInvalid(branch_id, "no open lane for this branch")
        lane.status, lane.stopped_at = "stopped", utc_now()
        self.repo.save_lane(lane)
        self._append_audit(
            walk,
            "explored_not_acted",
            {
                "walkId": walk.walk_id,
                "laneId": lane.lane_id,
                "branchNodeId": branch_id,
                "nodeIds": lane.node_ids,
            },
        )
        self.logger.log("lane_stopped", walkId=walk.walk_id, caseId=case_id, laneId=lane.lane_id)
        yield _event(
            "lane_closed", walkId=walk.walk_id, laneId=lane.lane_id, branchNodeId=branch_id
        )
