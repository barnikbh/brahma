// The workspace state machine (FR5.6, BR3.1–BR3.9, NFR2.2).
//
// Only `line` events add answer text. Progress uses a fixed label map, errors show the
// server's message, section headers use fixed titles. Nothing else from the model is
// ever stored for display. A follow-up's history confirmation is a fixed server line
// (pack drug names and fixed response words), shown as a notice.

import type {
  CaseView,
  DonePayload,
  FormField,
  FormKind,
  LockState,
  MapData,
  MapEdge,
  MapNode,
  Message,
  ProgressStep,
  WalkCounts,
  WalkEvent,
  WalkRequest,
} from "@/api/types";

export type WorkspaceStatus =
  | "empty"
  | "confirm"
  | "working"
  | "needs_data"
  | "answered"
  | "exploring"
  | "edit"
  | "out_of_knowledge"
  | "error"
  | "read_only";

// Fixed section headers (they are not model text, BR1.3 of U4).
export const SECTION_TITLES: Record<string, string> = {
  findings: "Findings",
  diagnosis: "Working diagnosis",
  tests: "Confirm and refine",
  subtype: "Refined sub-type",
  treatment: "Treatment tiers",
  monitor: "Monitor",
  diet: "Diet",
  watch_outs: "Watch-outs and surgery triggers",
  why: "Why",
  explore: "Exploring",
};

export const PROGRESS_LABELS: Record<ProgressStep, string> = {
  reading_findings: "Reading the findings",
  matching_diagnosis: "Matching a diagnosis in the graph",
  refining: "Refining with tests",
  planning_treatment: "Planning treatment tiers",
  checking_sources: "Checking lines against their sources",
  writing_explanation: "Writing the why",
};

export const FORM_TITLES: Record<FormKind, string> = {
  "confirm-findings": "Confirm findings",
  "needs-data": "Needs more data",
  "edit-treatment": "Edit treatment",
  "patient-details": "Patient details",
};

export type FormItemState = "open" | "submitting" | "submitted";

export interface SummaryInfo {
  outcome: DonePayload["outcome"];
  summary: string | null;
  counts: WalkCounts | null;
  packVersion: string | null;
  provider: string | null;
  model: string | null;
  sessionId: string | null;
  previousPackVersion: string | null;
  offers: string[];
  /** Chat text now starts a follow-up turn that reads it as treatment history. */
  followUp: boolean;
}

export type ChatItem =
  | { kind: "doctor"; id: string; text: string }
  | {
      kind: "form";
      id: string;
      formKind: FormKind;
      walkId: string | null;
      fields: FormField[];
      state: FormItemState;
      summary: string | null;
      nodeId?: string;
    }
  | { kind: "header"; id: string; sectionId: string; title: string; laneId: string | null }
  | {
      kind: "line";
      id: string;
      sectionId: string;
      text: string;
      nodeIds: string[];
      laneId: string | null;
    }
  | { kind: "summary"; id: string; info: SummaryInfo }
  | { kind: "notice"; id: string; text: string };

export interface MapState {
  version: string;
  nodes: MapNode[];
  edges: MapEdge[];
  lanes: Record<string, string[]>;
}

export interface WalkError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface WalkState {
  status: WorkspaceStatus;
  walkId: string | null;
  progress: ProgressStep | null;
  items: ChatItem[];
  map: MapState;
  error: WalkError | null;
  lastRequest: WalkRequest | null;
  done: SummaryInfo | null;
  readOnly: boolean;
  /** Open explore lanes by branch node ID. */
  openLanes: Record<string, string>;
  seq: number;
}

export const initialWalkState: WalkState = {
  status: "empty",
  walkId: null,
  progress: null,
  items: [],
  map: { version: "", nodes: [], edges: [], lanes: {} },
  error: null,
  lastRequest: null,
  done: null,
  readOnly: false,
  openLanes: {},
  seq: 0,
};

export type WalkAction =
  | { type: "request"; request: WalkRequest }
  | { type: "event"; event: WalkEvent }
  | { type: "request_failed"; error: WalkError }
  | { type: "form_submitted"; messageId: string; summary: string }
  | { type: "loaded"; view: CaseView }
  | { type: "map_loaded"; map: MapData }
  | { type: "lock"; state: LockState }
  | { type: "open_edit"; nodeId: string; fields: FormField[] }
  | { type: "edit_done"; formId: string; summary: string | null }
  | { type: "doctor_message"; text: string }
  | { type: "notice"; text: string };

/** What the screen shows: a read-only tab overrides every other state (BR3.9). */
export function viewStatus(state: WalkState): WorkspaceStatus {
  return state.readOnly ? "read_only" : state.status;
}

function nextId(state: WalkState, prefix: string): [string, number] {
  const seq = state.seq + 1;
  return [`${prefix}-${seq}`, seq];
}

function settledStatus(done: SummaryInfo | null): WorkspaceStatus {
  if (!done) return "answered";
  if (done.outcome === "out_of_knowledge") return "out_of_knowledge";
  if (done.outcome === "needs_data") return "needs_data";
  return "answered";
}

function formStatus(kind: FormKind): WorkspaceStatus {
  if (kind === "needs-data") return "needs_data";
  if (kind === "edit-treatment") return "edit";
  return "confirm";
}

function display(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

/** The one-line summary of a submitted form (BR3.1). Built from the doctor's own values. */
export function summarizeForm(
  kind: FormKind,
  fields: FormField[],
  values: Record<string, unknown>,
): string {
  if (kind === "confirm-findings") {
    const findings = Array.isArray(values.findings)
      ? (values.findings as Record<string, unknown>[])
      : [];
    const parts = findings.map((f) =>
      [display(f.name), display(f.value), display(f.unit), display(f.duration)]
        .filter(Boolean)
        .join(" "),
    );
    return `Confirmed findings: ${parts.join(" · ") || "none"}`;
  }
  if (kind === "needs-data") {
    const parts = fields.map((field) => {
      const value = display(values[field.name]);
      return `${field.label}: ${value || "not yet tested"}`;
    });
    return `Results: ${parts.join(" · ")}`;
  }
  const parts = Object.entries(values)
    .filter(([, v]) => display(v))
    .map(([k, v]) => `${k}: ${display(v)}`);
  return `${FORM_TITLES[kind]}: ${parts.join(" · ") || "no change"}`;
}

function markSubmitting(items: ChatItem[], to: FormItemState): ChatItem[] {
  return items.map((item) =>
    item.kind === "form" && item.state === "submitting" ? { ...item, state: to } : item,
  );
}

function addLine(
  state: WalkState,
  sectionId: string,
  text: string,
  nodeIds: string[],
  laneId: string | null,
): WalkState {
  let seq = state.seq;
  const items = [...state.items];
  let previous: Extract<ChatItem, { kind: "header" | "line" }> | undefined;
  for (let i = items.length - 1; i >= 0; i -= 1) {
    const item = items[i];
    if ((item.kind === "header" || item.kind === "line") && item.laneId === laneId) {
      previous = item;
      break;
    }
    if (item.kind === "summary" || item.kind === "form" || item.kind === "doctor") break;
  }
  if (!previous || previous.sectionId !== sectionId) {
    seq += 1;
    items.push({
      kind: "header",
      id: `h-${seq}`,
      sectionId,
      title: SECTION_TITLES[sectionId] ?? "Section",
      laneId,
    });
  }
  seq += 1;
  items.push({ kind: "line", id: `l-${seq}`, sectionId, text, nodeIds, laneId });
  return { ...state, items, seq };
}

function mergeMap(map: MapState, nodes: MapNode[], edges: MapEdge[], laneId?: string): MapState {
  if (laneId) {
    const known = new Set(map.nodes.map((n) => n.nodeId));
    const knownEdges = new Set(map.edges.map((e) => e.edgeId));
    return {
      ...map,
      nodes: [...map.nodes, ...nodes.filter((n) => !known.has(n.nodeId))],
      edges: [...map.edges, ...edges.filter((e) => !knownEdges.has(e.edgeId))],
      lanes: { ...map.lanes, [laneId]: nodes.map((n) => n.nodeId) },
    };
  }
  // A main-path update replaces the walk's map but keeps open explore lanes apart.
  const laneNodeIds = new Set(Object.values(map.lanes).flat());
  const mainIds = new Set(nodes.map((n) => n.nodeId));
  const laneNodes = map.nodes.filter((n) => laneNodeIds.has(n.nodeId) && !mainIds.has(n.nodeId));
  const laneEdges = map.edges.filter((e) => e.style === "exploring");
  return { ...map, nodes: [...nodes, ...laneNodes], edges: [...edges, ...laneEdges] };
}

function closeLane(map: MapState, laneId: string): MapState {
  const laneIds = new Set(map.lanes[laneId] ?? []);
  const lanes = { ...map.lanes };
  delete lanes[laneId];
  return {
    ...map,
    nodes: map.nodes.filter((n) => !(laneIds.has(n.nodeId) && n.status === "exploring")),
    edges: map.edges.filter(
      (e) => !(e.style === "exploring" && (laneIds.has(e.from) || laneIds.has(e.to))),
    ),
    lanes,
  };
}

function summaryFromDone(done: DonePayload): SummaryInfo {
  return {
    outcome: done.outcome,
    summary: done.outcome === "out_of_knowledge" ? (done.message ?? "No grounded answer") : null,
    counts: done.counts,
    packVersion: done.packVersion,
    provider: done.provider,
    model: done.model,
    sessionId: done.sessionId,
    previousPackVersion: done.previousPackVersion ?? null,
    offers: done.offers ?? [],
    followUp: done.followUp ?? false,
  };
}

function applyEvent(state: WalkState, event: WalkEvent): WalkState {
  switch (event.type) {
    case "progress":
      return { ...state, progress: event.payload.step };
    case "form": {
      const { kind, messageId, walkId, fields } = event.payload;
      const items = markSubmitting(state.items, "submitted").filter(
        (item) => !(item.kind === "form" && item.id === messageId),
      );
      items.push({
        kind: "form",
        id: messageId,
        formKind: kind,
        walkId,
        fields,
        state: "open",
        summary: null,
      });
      return { ...state, items, walkId, status: formStatus(kind), progress: null, error: null };
    }
    case "paused":
      return { ...state, walkId: event.payload.walkId, progress: null };
    case "map_update": {
      const { nodes, edges, laneId, walkId } = event.payload;
      return {
        ...state,
        walkId: laneId ? state.walkId : walkId,
        items: markSubmitting(state.items, "submitted"),
        map: mergeMap(state.map, nodes, edges, laneId),
      };
    }
    case "line": {
      const { sectionId, text, nodeIds, laneId } = event.payload;
      const next = addLine(state, sectionId, text, nodeIds, laneId ?? null);
      return { ...next, items: markSubmitting(next.items, "submitted") };
    }
    case "section_done":
      return state;
    case "done": {
      const info = summaryFromDone(event.payload);
      const [id, seq] = nextId(state, "s");
      return {
        ...state,
        seq,
        walkId: event.payload.walkId,
        items: [...markSubmitting(state.items, "submitted"), { kind: "summary", id, info }],
        done: info,
        status: settledStatus(info),
        progress: null,
        error: null,
        map: { ...state.map, version: event.payload.packVersion || state.map.version },
      };
    }
    case "error": {
      const { code, message, retryable, walkId } = event.payload;
      return {
        ...state,
        walkId: walkId ?? state.walkId,
        items: markSubmitting(state.items, "open"),
        status: "error",
        progress: null,
        error: { code, message, retryable },
      };
    }
    case "history": {
      const [id, seq] = nextId(state, "n");
      return {
        ...state,
        seq,
        walkId: event.payload.walkId,
        items: [...state.items, { kind: "notice", id, text: event.payload.text }],
      };
    }
    case "lane_closed": {
      const openLanes = { ...state.openLanes };
      delete openLanes[event.payload.branchNodeId];
      const [id, seq] = nextId(state, "n");
      return {
        ...state,
        seq,
        openLanes,
        map: closeLane(state.map, event.payload.laneId),
        items: [
          ...state.items,
          { kind: "notice", id, text: "Stopped exploring. The main plan is unchanged." },
        ],
        status: settledStatus(state.done),
        progress: null,
      };
    }
    default:
      return state;
  }
}

function itemsFromMessages(messages: Message[]): {
  items: ChatItem[];
  seq: number;
  summary: SummaryInfo | null;
} {
  let seq = 0;
  let summary: SummaryInfo | null = null;
  const answers = new Map<string, Record<string, unknown>>();
  for (const m of messages) {
    if (m.kind === "form_answer" && typeof m.body.formMessageId === "string") {
      answers.set(m.body.formMessageId, (m.body.values as Record<string, unknown>) ?? {});
    }
  }
  let state: WalkState = { ...initialWalkState };
  for (const m of messages) {
    if (m.kind === "text" && m.author === "doctor") {
      seq += 1;
      state = {
        ...state,
        items: [...state.items, { kind: "doctor", id: m.messageId, text: display(m.body.text) }],
      };
    } else if (m.kind === "text" && m.author === "brahma" && display(m.body.text)) {
      seq += 1;
      state = {
        ...state,
        items: [...state.items, { kind: "notice", id: m.messageId, text: display(m.body.text) }],
      };
    } else if (m.kind === "form") {
      const formKind = (m.formKind ?? "confirm-findings") as FormKind;
      const fields = Array.isArray(m.body.fields) ? (m.body.fields as FormField[]) : [];
      const submitted = m.formState === "submitted";
      const values = answers.get(m.messageId);
      state = {
        ...state,
        items: [
          ...state.items,
          {
            kind: "form",
            id: m.messageId,
            formKind,
            walkId: typeof m.body.walkId === "string" ? m.body.walkId : null,
            fields,
            state: submitted ? "submitted" : "open",
            summary: submitted ? summarizeForm(formKind, fields, values ?? {}) : null,
          },
        ],
      };
    } else if (m.kind === "pathway") {
      const sections = Array.isArray(m.body.sections)
        ? (m.body.sections as { sectionId: string; lines: { text: string; nodeIds: string[] }[] }[])
        : [];
      state = { ...state, seq };
      for (const section of sections) {
        for (const line of section.lines ?? []) {
          state = addLine(state, section.sectionId, line.text, line.nodeIds ?? [], null);
        }
      }
      seq = state.seq + 1;
      summary = {
        outcome: (m.body.outcome as SummaryInfo["outcome"]) ?? "answered",
        summary: display(m.body.summary) || null,
        counts: null,
        packVersion: display(m.body.packVersion) || null,
        provider: null,
        model: null,
        sessionId: typeof m.body.sessionId === "string" ? m.body.sessionId : null,
        previousPackVersion: null,
        offers: [],
        followUp: false,
      };
      state = {
        ...state,
        seq,
        items: [...state.items, { kind: "summary", id: `s-${seq}`, info: summary }],
      };
    }
    seq = Math.max(seq, state.seq);
  }
  return { items: state.items, seq: seq + 1, summary };
}

function fromCaseView(state: WalkState, view: CaseView): WalkState {
  const rebuilt = itemsFromMessages(view.messages);
  let summary = rebuilt.summary;
  const walk = view.walk;
  if (summary && walk) {
    summary = {
      ...summary,
      counts: walk.counts,
      packVersion: walk.packVersion,
      followUp: walk.canFollowUp ?? false,
    };
    const items = rebuilt.items.map((item) =>
      item.kind === "summary" && item.info === rebuilt.summary ? { ...item, info: summary! } : item,
    );
    rebuilt.items.splice(0, rebuilt.items.length, ...items);
  }
  let status: WorkspaceStatus = "empty";
  let error: WalkError | null = null;
  if (walk) {
    if (walk.status === "paused") {
      const open = [...rebuilt.items]
        .reverse()
        .find((item) => item.kind === "form" && item.state === "open");
      status = open && open.kind === "form" ? formStatus(open.formKind) : "working";
    } else if (walk.status === "error") {
      status = "error";
      error = {
        code: "walk_error",
        message: "The last walk stopped before it finished. Your entries are kept.",
        retryable: true,
      };
    } else {
      status = walk.status;
    }
  }
  return {
    ...state,
    items: rebuilt.items,
    seq: rebuilt.seq,
    walkId: walk?.walkId ?? null,
    status,
    error,
    done: summary,
    progress: null,
    readOnly: view.lock === "read_only",
    map: {
      ...state.map,
      version: walk?.packVersion ?? view.pinnedVersion ?? state.map.version,
    },
  };
}

export function walkReducer(state: WalkState, action: WalkAction): WalkState {
  switch (action.type) {
    case "request": {
      const { request } = action;
      const exploring = request.mode === "explore" || request.mode === "stop_explore";
      let next: WalkState = {
        ...state,
        lastRequest: request,
        status: exploring ? "exploring" : "working",
        error: null,
        progress: null,
      };
      if ((request.mode === "start" || request.mode === "follow_up") && request.text) {
        const [id, seq] = nextId(next, "d");
        next = { ...next, seq, items: [...next.items, { kind: "doctor", id, text: request.text }] };
      }
      if (request.mode === "explore" && request.branchNodeId) {
        next = { ...next, openLanes: { ...next.openLanes, [request.branchNodeId]: "pending" } };
      }
      return next;
    }
    case "event": {
      const next = applyEvent(state, action.event);
      const ev = action.event;
      if (ev.type === "map_update" && ev.payload.laneId) {
        const branch = Object.entries(next.openLanes).find(([, lane]) => lane === "pending");
        if (branch) {
          return { ...next, openLanes: { ...next.openLanes, [branch[0]]: ev.payload.laneId } };
        }
      }
      return next;
    }
    case "request_failed": {
      if (action.error.code === "case_read_only") {
        return { ...state, readOnly: true, progress: null, status: settledStatus(state.done) };
      }
      return {
        ...state,
        items: markSubmitting(state.items, "open"),
        status: "error",
        error: action.error,
        progress: null,
      };
    }
    case "form_submitted":
      return {
        ...state,
        items: state.items.map((item) =>
          item.kind === "form" && item.id === action.messageId
            ? { ...item, state: "submitting", summary: action.summary }
            : item,
        ),
      };
    case "loaded":
      return fromCaseView(state, action.view);
    case "map_loaded":
      return {
        ...state,
        map: {
          version: action.map.version || state.map.version,
          nodes: action.map.nodes,
          edges: action.map.edges,
          lanes: Object.fromEntries(
            (action.map.exploreLanes ?? []).map((lane) => [lane.laneId, lane.nodeIds]),
          ),
        },
      };
    case "lock":
      return { ...state, readOnly: action.state === "read_only" };
    case "open_edit": {
      const [id, seq] = nextId(state, "edit");
      return {
        ...state,
        seq,
        status: "edit",
        items: [
          ...state.items,
          {
            kind: "form",
            id,
            formKind: "edit-treatment",
            walkId: state.walkId,
            fields: action.fields,
            state: "open",
            summary: null,
            nodeId: action.nodeId,
          },
        ],
      };
    }
    case "edit_done":
      return {
        ...state,
        status: settledStatus(state.done),
        items: action.summary
          ? state.items.map((item) =>
              item.kind === "form" && item.id === action.formId
                ? { ...item, state: "submitted", summary: action.summary }
                : item,
            )
          : state.items.filter((item) => item.id !== action.formId),
      };
    case "doctor_message": {
      const [id, seq] = nextId(state, "d");
      return { ...state, seq, items: [...state.items, { kind: "doctor", id, text: action.text }] };
    }
    case "notice": {
      const [id, seq] = nextId(state, "n");
      return { ...state, seq, items: [...state.items, { kind: "notice", id, text: action.text }] };
    }
    default:
      return state;
  }
}

/** The request Retry sends: continue the same walk, or repeat a start that never began. */
export function retryRequest(state: WalkState): WalkRequest | null {
  if (state.walkId) return { mode: "continue", walkId: state.walkId };
  return state.lastRequest;
}
