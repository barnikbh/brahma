// A fake U4/U5 server for unit tests: fetch is replaced by a router over C8 and C9
// fixtures, including SSE streams of the recorded demo walk. All data is synthetic.

import { vi } from "vitest";
import type {
  BrowseDetail,
  CaseView,
  Health,
  MapNode,
  NodeDetail,
  PackGraph,
  Profile,
  Proposal,
  SessionDetail,
  SessionSummary,
  SessionView,
  UpdateThread,
  WalkEvent,
} from "@/api/types";

export const DEMO_TEXT =
  "34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g";

export const MAYA: Profile = {
  profileId: "p-maya",
  displayName: "Dr. Maya (demo)",
  role: "doctor",
  specialty: "gastroenterology",
  demoRegistration: "DEMO-REG-0001",
  listed: true,
};

export const REVIEWER: Profile = {
  profileId: "p-reviewer",
  displayName: "Demo clinical reviewer",
  role: "reviewer",
  demoRegistration: "DEMO-REG-0003",
  listed: true,
};

export function sessionView(profile: Profile = MAYA, needsDisclaimer = false): SessionView {
  return {
    profile,
    packVersions: "IBD 1.0; URO 0.1",
    needsDisclaimer,
    disclaimer: {
      version: "1.0",
      text: "Decision support, not diagnosis. Brahma shows cited knowledge-graph content for synthetic cases only.",
    },
    provider: { provider: "recorded", model: "recorded" },
  };
}

export const HEALTH: Health = {
  status: "ok",
  packs: [
    { pack: "IBD", number: "1.0" },
    { pack: "URO", number: "0.1" },
  ],
  provider: { provider: "recorded", model: "recorded" },
  database: "ok",
  disclaimer: "Decision support, not diagnosis",
};

export function caseView(overrides: Partial<CaseView> = {}): CaseView {
  return {
    case: {
      caseId: "BR-000001",
      patientId: "pt-1",
      ownerProfileId: "p-maya",
      pinnedPackVersion: null,
      origin: "clinic",
      status: "new",
      synthetic: true,
      createdAt: "2026-10-30T10:00:00Z",
      updatedAt: "2026-10-30T10:00:00Z",
    },
    patient: {
      patientId: "pt-1",
      syntheticName: "Demo Patient A",
      age: 34,
      sex: "female",
      weightKg: 58,
      comorbidities: [],
      allergies: ["penicillin"],
      currentMedication: [],
    },
    messages: [],
    formDrafts: {},
    findings: [],
    pinnedVersion: null,
    newerVersion: null,
    lock: "held",
    walk: null,
    disclaimer: "Decision support, not diagnosis",
    ...overrides,
  };
}

const node = (
  nodeId: string,
  type: string,
  label: string,
  column: string,
  status: MapNode["status"],
  result: string | null = null,
): MapNode => ({
  nodeId,
  type,
  label,
  column,
  status,
  result: result ? { value: result } : null,
});

export const DEMO_NODES: MapNode[] = [
  node("IBD-N1", "symptom", "Bloody diarrhoea", "findings", "used"),
  node("IBD-N3", "metric", "Haemoglobin below 10.5 g/dL", "findings", "used"),
  node("IBD-N10", "diagnosis", "Suspected IBD", "diagnosis", "used"),
  node("IBD-N12", "diagnosis", "Infectious colitis", "diagnosis", "not_taken"),
  node("IBD-N20", "test", "Stool culture", "tests", "used", "negative"),
  node("IBD-N21", "test", "Ileocolonoscopy", "tests", "used", "ulcerative colitis"),
  node("IBD-N34", "subtype", "Acute severe UC", "subtype", "used"),
  node("IBD-N50", "treatment_tier", "UC Tier 2", "treatment", "entry"),
  node("IBD-N51", "drug", "Hydrocortisone 100 mg IV", "treatment", "used"),
];

export const START_EVENTS: WalkEvent[] = [
  { type: "progress", payload: { step: "reading_findings" } },
  {
    type: "form",
    payload: {
      kind: "confirm-findings",
      messageId: "msg-1",
      walkId: "wk-1",
      fields: [
        {
          name: "age",
          label: "age 34",
          kind: "finding",
          findingKind: "age",
          value: 34,
          unit: "years",
          validationState: "ok",
        },
        {
          name: "bloody stool",
          label: "bloody stool",
          kind: "finding",
          findingKind: "symptom",
          value: null,
          duration: "6 months",
          validationState: "ok",
        },
        {
          name: "Hb",
          label: "Hb 10.2",
          kind: "finding",
          findingKind: "metric",
          value: 10.2,
          unit: "g/dL",
          validationState: "ok",
        },
      ],
    },
  },
  { type: "paused", payload: { walkId: "wk-1", waitingFor: "msg-1" } },
];

export const NEEDS_DATA_EVENTS: WalkEvent[] = [
  { type: "progress", payload: { step: "matching_diagnosis" } },
  {
    type: "map_update",
    payload: { walkId: "wk-1", nodes: DEMO_NODES.slice(0, 4), edges: [] },
  },
  {
    type: "form",
    payload: {
      kind: "needs-data",
      messageId: "msg-2",
      walkId: "wk-1",
      fields: [
        {
          name: "IBD-N20",
          label: "Stool culture",
          kind: "test_result",
          nodeId: "IBD-N20",
          options: ["negative", "positive"],
        },
        {
          name: "IBD-N21",
          label: "Ileocolonoscopy",
          kind: "test_result",
          nodeId: "IBD-N21",
          options: ["ulcerative colitis", "crohn's disease", "normal"],
        },
      ],
    },
  },
  { type: "paused", payload: { walkId: "wk-1", waitingFor: "msg-2" } },
];

export const ANSWER_EVENTS: WalkEvent[] = [
  { type: "progress", payload: { step: "matching_diagnosis" } },
  {
    type: "map_update",
    payload: {
      walkId: "wk-1",
      nodes: DEMO_NODES,
      edges: [
        { edgeId: "e1", from: "IBD-N1", to: "IBD-N10", style: "walked" },
        { edgeId: "e2", from: "IBD-N10", to: "IBD-N12", style: "not_taken" },
      ],
    },
  },
  {
    type: "line",
    payload: {
      sectionId: "findings",
      text: "Visible blood in loose stools is a key presenting feature to assess.",
      nodeIds: ["IBD-N1"],
    },
  },
  {
    type: "line",
    payload: {
      sectionId: "findings",
      text: "A haemoglobin below 10.5 g/dL counts as a marker of systemic toxicity.",
      nodeIds: ["IBD-N3"],
    },
  },
  { type: "section_done", payload: { walkId: "wk-1", sectionId: "findings", title: "Findings" } },
  { type: "progress", payload: { step: "planning_treatment" } },
  {
    type: "line",
    payload: {
      sectionId: "treatment",
      text: "Intravenous hydrocortisone is a first-line option at the Tier 2 entry point.",
      nodeIds: ["IBD-N50", "IBD-N51"],
    },
  },
  {
    type: "section_done",
    payload: { walkId: "wk-1", sectionId: "treatment", title: "Treatment tiers" },
  },
  {
    type: "done",
    payload: {
      walkId: "wk-1",
      sessionId: "s-1",
      outcome: "answered",
      counts: { steps: 9, cited: 3, ungrounded: 0 },
      packVersion: "IBD 1.0",
      provider: "recorded",
      model: "recorded",
      disclaimer: "Decision support, not diagnosis",
      offers: [],
      followUp: true,
    },
  },
];

export const FOLLOW_UP_TEXT = "Remicade failed. steroids work. Suggest alternate treatment plan";

export const FOLLOW_UP_NODES: MapNode[] = [
  ...DEMO_NODES.filter((n) => n.nodeId !== "IBD-N50").concat(
    node("IBD-N50", "treatment_tier", "UC Tier 2", "treatment", "used"),
  ),
  {
    ...node("IBD-N53", "drug", "Infliximab 5 mg/kg IV", "treatment", "tried"),
    result: { response: "failed" },
  },
  node("IBD-N46", "treatment_tier", "UC after anti-TNF failure", "treatment", "entry"),
  node("IBD-N54", "drug", "Ustekinumab 90 mg SC maintenance", "treatment", "used"),
];

export const FOLLOW_UP_EVENTS: WalkEvent[] = [
  { type: "progress", payload: { step: "reading_findings" } },
  {
    type: "history",
    payload: {
      walkId: "wk-2",
      text: "Noted treatment history: infliximab — no response; corticosteroid — responded.",
      therapies: [
        { drug: "infliximab", response: "failed", nodeIds: ["IBD-N53"] },
        { drug: "corticosteroid", response: "responded", nodeIds: ["IBD-N51"] },
      ],
    },
  },
  { type: "map_update", payload: { walkId: "wk-2", nodes: FOLLOW_UP_NODES, edges: [] } },
  { type: "progress", payload: { step: "planning_treatment" } },
  {
    type: "line",
    payload: {
      sectionId: "treatment",
      text: "Ustekinumab starts with one weight-based intravenous induction dose, then 90 mg under the skin every 8 weeks.",
      nodeIds: ["IBD-N54"],
    },
  },
  {
    type: "section_done",
    payload: { walkId: "wk-2", sectionId: "treatment", title: "Treatment tiers" },
  },
  {
    type: "done",
    payload: {
      walkId: "wk-2",
      sessionId: "s-2",
      outcome: "answered",
      counts: { steps: 12, cited: 1, ungrounded: 0 },
      packVersion: "IBD 1.1",
      provider: "recorded",
      model: "recorded",
      disclaimer: "Decision support, not diagnosis",
      offers: [],
      followUp: true,
    },
  },
];

export function nodeDetail(overrides: Partial<NodeDetail> = {}): NodeDetail {
  return {
    node: {
      nodeId: "IBD-N51",
      type: "drug",
      label: "Hydrocortisone 100 mg IV",
      content: "Paraphrased pack content: an intravenous steroid regimen for acute severe UC.",
      fields: {
        drug: "hydrocortisone",
        route: "intravenous",
        doseValue: 100,
        doseUnit: "mg",
        doseBasis: "absolute",
        frequency: "four times daily",
        duration: "review on day 3",
      },
      sourceIds: ["SRC-1"],
      column: "treatment",
    },
    sources: [
      { sourceId: "SRC-1", title: "Synthetic guideline", year: 2019, section: "Acute severe UC" },
    ],
    comments: [],
    safety: [
      {
        check: "allergy",
        status: "conflict",
        nodeIds: ["IBD-N101"],
        message: "penicillin class",
        drugNodeId: "IBD-N51",
      },
      {
        check: "interaction",
        status: "not_checked",
        nodeIds: [],
        message: "Not checked: no grounded safety data",
        drugNodeId: "IBD-N51",
      },
    ],
    dose: { value: 100, unit: "mg", formula: "100 mg (fixed dose)" },
    edited: null,
    leadsTo: [],
    nextPaths: [],
    packVersion: "IBD 1.0",
    disclaimer: "Decision support, not diagnosis",
    ...overrides,
  };
}

export const SESSIONS: SessionSummary[] = [
  {
    sessionId: "s-1",
    caseId: "BR-000001",
    createdAt: "2026-10-30T10:05:00Z",
    label: "Ulcerative colitis → Acute severe UC",
    outcome: "answered",
    packVersion: "IBD 1.0",
  },
];

export const SESSION_DETAIL: SessionDetail = {
  record: {
    sessionId: "s-1",
    createdAt: "2026-10-30T10:05:00Z",
    caseId: "BR-000001",
    walkId: "wk-1",
    profileId: "p-maya",
    packVersion: "IBD 1.0",
    provider: "recorded",
    model: "recorded",
    inputs: { text: DEMO_TEXT, findings: [] },
    pathNodeIds: ["IBD-N1", "IBD-N10"],
    answer: {
      summary: "Ulcerative colitis → Acute severe UC",
      sections: [
        {
          sectionId: "findings",
          title: "Findings",
          lines: [{ text: "Visible blood in loose stools is a key feature.", nodeIds: ["IBD-N1"] }],
        },
      ],
      counts: { steps: 2, cited: 1, ungrounded: 0 },
    },
    sources: ["SRC-1"],
    explanation: [{ text: "Bloody diarrhoea pointed to IBD.", nodeIds: ["IBD-N1", "IBD-N10"] }],
    outcome: "answered",
  },
  entries: [
    {
      entryId: "a-1",
      createdAt: "2026-10-30T10:05:00Z",
      kind: "session_recorded",
      profileId: "p-maya",
      payload: {},
    },
  ],
  map: {
    version: "IBD 1.0",
    nodes: [
      node("IBD-N1", "symptom", "Bloody diarrhoea", "findings", "used"),
      node("IBD-N10", "diagnosis", "Suspected IBD", "diagnosis", "used"),
    ],
    edges: [{ edgeId: "e1", from: "IBD-N1", to: "IBD-N10", style: "walked" }],
    selectedPath: ["IBD-N1", "IBD-N10"],
  },
  disclaimer: "Decision support, not diagnosis",
};

export function proposal(overrides: Partial<Proposal> = {}): Proposal {
  return {
    proposalId: "pr-1",
    pack: "IBD",
    baseVersion: "1.0",
    targetVersion: "1.1",
    proposerProfileId: "p-maya",
    origin: "doctor",
    comment: "Clarify the review day",
    status: "proposed",
    sourceId: null,
    reviewerProfileId: null,
    reviewComment: null,
    publishedVersion: null,
    createdAt: "2026-10-30T10:00:00Z",
    decidedAt: null,
    changes: [
      {
        nodeId: "IBD-N51",
        before: { content: "Old paraphrase." },
        after: { content: "New paraphrase." },
        sourcePassage: "A synthetic source passage.",
        copyFlag: false,
      },
    ],
    copyFlaggedNodeIds: [],
    ...overrides,
  };
}

export const BROWSE_GRAPH: PackGraph = {
  pack: "IBD",
  version: "1.1",
  initialVersion: "1.1",
  nodes: [
    {
      nodeId: "IBD-N1",
      type: "symptom",
      label: "Bloody diarrhoea",
      column: "findings",
      updatedAt: null,
    },
    {
      nodeId: "IBD-N2",
      type: "diagnosis",
      label: "Ulcerative colitis",
      column: "diagnosis",
      updatedAt: null,
    },
    {
      nodeId: "IBD-N54",
      type: "drug",
      label: "Ustekinumab 90 mg SC",
      column: "treatment",
      updatedAt: null,
    },
  ],
  edges: [],
};

export function browseDetail(nodeId: string, overrides: Partial<BrowseDetail> = {}): BrowseDetail {
  const meta = BROWSE_GRAPH.nodes.find((n) => n.nodeId === nodeId) ?? BROWSE_GRAPH.nodes[0];
  const next: Record<string, BrowseDetail["outgoing"]> = {
    "IBD-N1": [
      {
        edgeId: "E1",
        nodeId: "IBD-N2",
        type: "diagnosis",
        label: "Ulcerative colitis",
        relation: "suggests",
        relationLabel: "suggests",
      },
    ],
    "IBD-N2": [
      {
        edgeId: "E2",
        nodeId: "IBD-N54",
        type: "drug",
        label: "Ustekinumab 90 mg SC",
        relation: "first_line",
        relationLabel: "first line",
      },
    ],
  };
  return {
    node: {
      nodeId,
      type: meta.type,
      label: meta.label,
      content: `Content of ${meta.label}.`,
      fields: nodeId === "IBD-N54" ? { doseValue: 90, route: "SC" } : {},
      sourceIds: ["S1"],
      column: meta.column,
    },
    sources: [
      { sourceId: "S1", title: "A synthetic guideline", year: 2022, section: "Intro", url: null },
    ],
    comments: [],
    outgoing: next[nodeId] ?? [],
    incoming:
      nodeId === "IBD-N2"
        ? [
            {
              edgeId: "E1",
              nodeId: "IBD-N1",
              type: "symptom",
              label: "Bloody diarrhoea",
              relation: "suggests",
              relationLabel: "suggests",
            },
          ]
        : [],
    updated: null,
    initialVersion: "1.1",
    packVersion: "IBD 1.1",
    ...overrides,
  };
}

export function thread(overrides: Partial<UpdateThread> = {}): UpdateThread {
  return {
    threadId: "th-1",
    pack: "IBD",
    profileId: "p-maya",
    profileName: "Dr. Maya (demo)",
    status: "open",
    rounds: 0,
    createdAt: "2026-10-30T10:00:00Z",
    updatedAt: "2026-10-30T10:00:00Z",
    messages: [],
    proposals: [],
    ...overrides,
  };
}

// --- The fake fetch -----------------------------------------------------------------------

export interface FakeCall {
  method: string;
  path: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
}

export type FakeReply = Response | Promise<Response> | WalkEvent[] | object | null;
export type FakeHandler = (call: FakeCall) => FakeReply;

const encoder = new TextEncoder();

/** SSE text for events, in C8 framing. */
export function sseText(events: WalkEvent[]): string {
  return events.map((e) => `event: ${e.type}\ndata: ${JSON.stringify(e.payload)}\n\n`).join("");
}

/** A byte stream of the given text, split into chunks of `size` characters. */
export function streamOf(text: string, size = 17): ReadableStream<Uint8Array> {
  const chunks: string[] = [];
  for (let i = 0; i < text.length; i += size) chunks.push(text.slice(i, i + size));
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

export function json(body: unknown, status = 200): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function apiError(status: number, code: string, message: string, retryable = false) {
  return json({ error: { code, message, retryable } }, status);
}

export function sse(events: WalkEvent[]): Response {
  return new Response(streamOf(sseText(events)), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function defaults(): Record<string, FakeHandler> {
  return {
    "GET /api/health": () => HEALTH,
    "GET /api/profiles": () => ({ profiles: [MAYA, REVIEWER] }),
    "GET /api/session": () => sessionView(),
    "POST /api/session": () => sessionView(MAYA, true),
    "DELETE /api/session": () => new Response(null, { status: 204 }),
    "POST /api/disclaimer": () => ({
      acceptanceId: "acc-1",
      packVersions: "IBD 1.0; URO 0.1",
      disclaimer: "Decision support, not diagnosis",
    }),
    "GET /api/features": () => ({ features: [{ name: "knowledge" }] }),
    "GET /api/patients": () => ({ results: [], query: "" }),
    "POST /api/patients": () => json(caseView(), 201),
    "GET /api/cases/:id": () => caseView(),
    "POST /api/cases/:id/lock": () => ({ state: "held" }),
    "DELETE /api/cases/:id/lock": () => new Response(null, { status: 204 }),
    "GET /api/cases/:id/map": () => ({
      version: "IBD 1.0",
      nodes: [],
      edges: [],
      selectedPath: [],
    }),
    "GET /api/nodes/:v/:n": () => nodeDetail(),
    "GET /api/sessions": () => ({ sessions: SESSIONS }),
    "GET /api/sessions/:id": () => SESSION_DETAIL,
    "GET /api/knowledge/proposals": () => ({ proposals: [proposal()] }),
    "GET /api/knowledge/packs": () => ({
      packs: [
        { pack: "IBD", name: "Inflammatory bowel disease", liveVersion: "1.1", versions: ["1.1"] },
      ],
    }),
    "GET /api/knowledge/graph": () => BROWSE_GRAPH,
    "GET /api/knowledge/nodes/:id": (call) => browseDetail(call.path.split("/").pop() ?? "IBD-N1"),
    "GET /api/knowledge/updates": () => ({ threads: [] }),
    "GET /api/knowledge/versions": () => ({
      pack: "IBD",
      versions: [
        {
          version: "1.0",
          status: "live",
          date: "2026-10-29T10:00:00Z",
          author: "seed",
          change: "First version",
          comment: null,
          proposalId: null,
        },
      ],
    }),
  };
}

function matches(pattern: string, path: string): boolean {
  const a = pattern.split("/");
  const b = path.split("/");
  return a.length === b.length && a.every((part, i) => part.startsWith(":") || part === b[i]);
}

export interface FakeApi {
  calls: FakeCall[];
  /** Replace or add a route handler, e.g. `"POST /api/cases/:id/walk"`. */
  on: (route: string, handler: FakeHandler) => void;
  /** Queue the SSE streams the walk route answers with, one per POST. */
  walkStreams: WalkEvent[][];
  callsTo: (method: string, path: string) => FakeCall[];
}

export function installFakeApi(routes: Record<string, FakeHandler> = {}): FakeApi {
  const table: Record<string, FakeHandler> = { ...defaults(), ...routes };
  const api: FakeApi = {
    calls: [],
    walkStreams: [],
    on: (route, handler) => {
      table[route] = handler;
    },
    callsTo: (method, path) =>
      api.calls.filter((c) => c.method === method && matches(path, c.path)),
  };
  table["POST /api/cases/:id/walk"] ??= () => sse(api.walkStreams.shift() ?? []);

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = typeof input === "string" ? input : input.toString();
    const parsed = new URL(url, "http://localhost");
    const method = (init.method ?? "GET").toUpperCase();
    const headers = Object.fromEntries(
      Object.entries((init.headers ?? {}) as Record<string, string>).map(([k, v]) => [
        k.toLowerCase(),
        v,
      ]),
    );
    const body = typeof init.body === "string" ? (JSON.parse(init.body) as unknown) : undefined;
    const call: FakeCall = { method, path: parsed.pathname, url, headers, body };
    api.calls.push(call);
    const key = Object.keys(table)
      .sort((x, y) => y.length - x.length)
      .find((route) => {
        const [m, p] = route.split(" ");
        return m === method && matches(p, parsed.pathname);
      });
    if (!key) return apiError(404, "http_404", `No fake route for ${method} ${parsed.pathname}`);
    const reply = await table[key](call);
    if (reply instanceof Response) return reply;
    if (Array.isArray(reply)) return sse(reply as WalkEvent[]);
    return json(reply);
  });
  vi.stubGlobal("fetch", fetchMock);
  return api;
}
