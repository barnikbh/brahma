import { describe, expect, it } from "vitest";
import type { WalkEvent } from "@/api/types";
import {
  ANSWER_EVENTS,
  DEMO_TEXT,
  FOLLOW_UP_EVENTS,
  FOLLOW_UP_TEXT,
  NEEDS_DATA_EVENTS,
  START_EVENTS,
  caseView,
} from "@/test/fakeApi";
import {
  initialWalkState,
  retryRequest,
  summarizeForm,
  viewStatus,
  walkReducer,
  type ChatItem,
  type WalkAction,
  type WalkState,
} from "./walkReducer";

function run(state: WalkState, actions: WalkAction[]): WalkState {
  return actions.reduce(walkReducer, state);
}

const events = (list: WalkEvent[]): WalkAction[] => list.map((event) => ({ type: "event", event }));

function demoState(): WalkState {
  return run(initialWalkState, [
    { type: "request", request: { mode: "start", text: DEMO_TEXT } },
    ...events(START_EVENTS),
    { type: "form_submitted", messageId: "msg-1", summary: "Confirmed findings" },
    { type: "request", request: { mode: "continue", walkId: "wk-1", formMessageId: "msg-1" } },
    ...events(NEEDS_DATA_EVENTS),
    { type: "form_submitted", messageId: "msg-2", summary: "Results" },
    { type: "request", request: { mode: "continue", walkId: "wk-1", formMessageId: "msg-2" } },
    ...events(ANSWER_EVENTS),
  ]);
}

const lines = (state: WalkState) =>
  state.items.filter((i): i is Extract<ChatItem, { kind: "line" }> => i.kind === "line");

describe("walkReducer", () => {
  it("renders a follow-up turn like a walk: doctor text, history notice, map, lines", () => {
    const answered = demoState();
    expect(answered.done?.followUp).toBe(true);
    const state = run(answered, [
      { type: "request", request: { mode: "follow_up", text: FOLLOW_UP_TEXT } },
      ...events(FOLLOW_UP_EVENTS),
    ]);
    const tail = state.items.slice(answered.items.length);
    expect(tail.map((i) => i.kind)).toEqual(["doctor", "notice", "header", "line", "summary"]);
    expect(tail[1]).toMatchObject({
      text: "Noted treatment history: infliximab — no response; corticosteroid — responded.",
    });
    expect(tail[2]).toMatchObject({ title: "Treatment tiers" });
    expect(state.walkId).toBe("wk-2");
    expect(state.status).toBe("answered");
    expect(state.map.nodes.find((n) => n.nodeId === "IBD-N53")?.status).toBe("tried");
    expect(state.map.version).toBe("IBD 1.1");
  });

  it("rebuilds a follow-up's confirmation and its follow-up state from the case view", () => {
    const view = caseView({
      messages: [
        {
          messageId: "m-1",
          caseId: "BR-000001",
          author: "brahma",
          kind: "text",
          body: { text: "Noted treatment history: infliximab — no response." },
          formKind: null,
          formState: null,
          createdAt: "2026-10-30T10:00:00Z",
        },
        {
          messageId: "m-2",
          caseId: "BR-000001",
          author: "brahma",
          kind: "pathway",
          body: { outcome: "answered", sections: [], packVersion: "IBD 1.1" },
          formKind: null,
          formState: null,
          createdAt: "2026-10-30T10:00:01Z",
        },
      ],
      walk: {
        walkId: "wk-2",
        status: "answered",
        waitingFor: null,
        lastSectionDone: 7,
        counts: { steps: 1, cited: 1, ungrounded: 0 },
        packVersion: "IBD 1.1",
        canFollowUp: true,
      },
    });
    const state = walkReducer(initialWalkState, { type: "loaded", view });
    expect(state.items[0]).toMatchObject({ kind: "notice" });
    expect(state.done?.followUp).toBe(true);
  });

  it("walks the demo sequence to answered with lines under the right sections", () => {
    let state = run(initialWalkState, [
      { type: "request", request: { mode: "start", text: DEMO_TEXT } },
      ...events(START_EVENTS),
    ]);
    expect(state.status).toBe("confirm");
    expect(state.walkId).toBe("wk-1");
    state = demoState();
    expect(state.status).toBe("answered");
    expect(lines(state).map((l) => l.sectionId)).toEqual(["findings", "findings", "treatment"]);
    const headers = state.items.filter((i) => i.kind === "header").map((h) => h.title);
    expect(headers).toEqual(["Findings", "Treatment tiers"]);
    const forms = state.items.filter((i) => i.kind === "form");
    expect(forms.every((f) => f.kind === "form" && f.state === "submitted")).toBe(true);
    expect(state.done?.counts).toEqual({ steps: 9, cited: 3, ungrounded: 0 });
    expect(state.map.nodes).toHaveLength(9);
    expect(state.map.version).toBe("IBD 1.0");
  });

  it("never adds answer text from progress, section_done or map events", () => {
    const state = run(initialWalkState, [
      { type: "request", request: { mode: "continue", walkId: "wk-1" } },
      { type: "event", event: { type: "progress", payload: { step: "planning_treatment" } } },
      {
        type: "event",
        event: {
          type: "section_done",
          payload: { walkId: "wk-1", sectionId: "treatment", title: "<b>model text</b>" },
        },
      },
    ]);
    expect(state.progress).toBe("planning_treatment");
    expect(state.items).toEqual([]);
    expect(JSON.stringify(state)).not.toContain("model text");
  });

  it("keeps the inputs on error and retries with continue and the same walkId", () => {
    let state = run(initialWalkState, [
      { type: "request", request: { mode: "start", text: DEMO_TEXT } },
      ...events(START_EVENTS),
      { type: "form_submitted", messageId: "msg-1", summary: "Confirmed" },
      { type: "request", request: { mode: "continue", walkId: "wk-1", formMessageId: "msg-1" } },
      {
        type: "event",
        event: {
          type: "error",
          payload: {
            code: "model_timeout",
            message: "The model provider did not answer in time.",
            retryable: true,
            walkId: "wk-1",
          },
        },
      },
    ]);
    expect(viewStatus(state)).toBe("error");
    expect(state.error?.message).toBe("The model provider did not answer in time.");
    const form = state.items.find((i) => i.kind === "form");
    expect(form && form.kind === "form" && form.state).toBe("open");
    expect(state.items[0]).toEqual({ kind: "doctor", id: expect.any(String), text: DEMO_TEXT });
    expect(retryRequest(state)).toEqual({ mode: "continue", walkId: "wk-1" });
    state = walkReducer(
      { ...initialWalkState, lastRequest: { mode: "start", text: "x" } },
      {
        type: "request_failed",
        error: { code: "server_unreachable", message: "down", retryable: true },
      },
    );
    expect(retryRequest(state)).toEqual({ mode: "start", text: "x" });
  });

  it("shows out of knowledge with its message", () => {
    const state = run(initialWalkState, [
      { type: "request", request: { mode: "continue", walkId: "wk-2" } },
      {
        type: "event",
        event: { type: "map_update", payload: { walkId: "wk-2", nodes: [], edges: [] } },
      },
      {
        type: "event",
        event: {
          type: "done",
          payload: {
            walkId: "wk-2",
            sessionId: "s-2",
            outcome: "out_of_knowledge",
            counts: { steps: 0, cited: 0, ungrounded: 0 },
            packVersion: "IBD 1.0",
            provider: "recorded",
            model: "recorded",
            disclaimer: "Decision support, not diagnosis",
            message: "No grounded answer",
            offers: ["suggest_branch"],
          },
        },
      },
    ]);
    expect(state.status).toBe("out_of_knowledge");
    expect(state.done?.summary).toBe("No grounded answer");
    expect(lines(state)).toHaveLength(0);
  });

  it("keeps the explore lane apart from the main plan and closes it", () => {
    let state = demoState();
    const mainLines = lines(state).length;
    state = run(state, [
      { type: "request", request: { mode: "explore", walkId: "wk-1", branchNodeId: "IBD-N12" } },
      {
        type: "event",
        event: {
          type: "map_update",
          payload: {
            walkId: "wk-1",
            laneId: "ln-1",
            nodes: [
              {
                nodeId: "IBD-N60",
                type: "test",
                label: "Stool PCR",
                column: "tests",
                status: "exploring",
                result: null,
              },
            ],
            edges: [{ edgeId: "x1", from: "IBD-N12", to: "IBD-N60", style: "exploring" }],
          },
        },
      },
      {
        type: "event",
        event: {
          type: "line",
          payload: {
            sectionId: "explore",
            laneId: "ln-1",
            text: "Explored line.",
            nodeIds: ["IBD-N60"],
          },
        },
      },
      {
        type: "event",
        event: {
          type: "section_done",
          payload: { walkId: "wk-1", sectionId: "explore", laneId: "ln-1", title: "Exploring" },
        },
      },
    ]);
    expect(state.status).toBe("exploring");
    expect(state.openLanes).toEqual({ "IBD-N12": "ln-1" });
    expect(lines(state).filter((l) => l.laneId === "ln-1")).toHaveLength(1);
    expect(lines(state).filter((l) => !l.laneId)).toHaveLength(mainLines);
    expect(state.map.lanes["ln-1"]).toEqual(["IBD-N60"]);
    state = walkReducer(state, {
      type: "event",
      event: {
        type: "lane_closed",
        payload: { walkId: "wk-1", laneId: "ln-1", branchNodeId: "IBD-N12" },
      },
    });
    expect(state.status).toBe("answered");
    expect(state.map.nodes.find((n) => n.nodeId === "IBD-N60")).toBeUndefined();
    expect(state.openLanes).toEqual({});
  });

  it("turns read-only on a lock refusal or a 409 case_read_only", () => {
    let state = walkReducer(initialWalkState, { type: "lock", state: "read_only" });
    expect(viewStatus(state)).toBe("read_only");
    state = walkReducer(initialWalkState, {
      type: "request_failed",
      error: { code: "case_read_only", message: "read-only", retryable: false },
    });
    expect(state.readOnly).toBe(true);
  });

  it("rebuilds the thread from a reopened case view", () => {
    const view = caseView({
      pinnedVersion: "IBD 1.0",
      lock: "read_only",
      walk: {
        walkId: "wk-1",
        status: "answered",
        waitingFor: null,
        lastSectionDone: 8,
        counts: { steps: 9, cited: 1, ungrounded: 0 },
        packVersion: "IBD 1.0",
      },
      messages: [
        {
          messageId: "m1",
          caseId: "BR-000001",
          author: "doctor",
          kind: "text",
          body: { text: DEMO_TEXT },
          formKind: null,
          formState: null,
          createdAt: "t",
        },
        {
          messageId: "m2",
          caseId: "BR-000001",
          author: "brahma",
          kind: "form",
          body: {
            walkId: "wk-1",
            fields: [{ name: "IBD-N20", label: "Stool culture", kind: "test_result" }],
          },
          formKind: "needs-data",
          formState: "submitted",
          createdAt: "t",
        },
        {
          messageId: "m3",
          caseId: "BR-000001",
          author: "doctor",
          kind: "form_answer",
          body: { formMessageId: "m2", values: { "IBD-N20": "negative" } },
          formKind: null,
          formState: null,
          createdAt: "t",
        },
        {
          messageId: "m4",
          caseId: "BR-000001",
          author: "brahma",
          kind: "pathway",
          body: {
            outcome: "answered",
            summary: "UC",
            packVersion: "IBD 1.0",
            sessionId: "s-1",
            sections: [
              {
                sectionId: "findings",
                title: "Findings",
                lines: [{ text: "Checked line.", nodeIds: ["IBD-N1"] }],
              },
            ],
          },
          formKind: null,
          formState: null,
          createdAt: "t",
        },
      ],
    });
    const state = walkReducer(initialWalkState, { type: "loaded", view });
    expect(viewStatus(state)).toBe("read_only");
    expect(state.status).toBe("answered");
    expect(lines(state).map((l) => l.text)).toEqual(["Checked line."]);
    const form = state.items.find((i) => i.kind === "form");
    expect(form && form.kind === "form" && form.summary).toBe("Results: Stool culture: negative");
    expect(state.done?.counts?.cited).toBe(1);
  });

  it("summarises submitted forms from the doctor's own values", () => {
    expect(
      summarizeForm("confirm-findings", [], {
        findings: [
          { name: "Hb", value: 10.2, unit: "g/dL" },
          { name: "bloody stool", duration: "6 months" },
        ],
      }),
    ).toBe("Confirmed findings: Hb 10.2 g/dL · bloody stool 6 months");
    expect(
      summarizeForm("needs-data", [{ name: "N22", label: "Extent", kind: "test_result" }], {}),
    ).toBe("Results: Extent: not yet tested");
    expect(summarizeForm("edit-treatment", [], { doseValue: 40 })).toBe(
      "Edit treatment: doseValue: 40",
    );
  });

  it("opens and closes a local edit-treatment form", () => {
    let state = demoState();
    state = walkReducer(state, { type: "open_edit", nodeId: "IBD-N51", fields: [] });
    expect(state.status).toBe("edit");
    const form = state.items.at(-1);
    expect(form).toMatchObject({ kind: "form", formKind: "edit-treatment", nodeId: "IBD-N51" });
    state = walkReducer(state, {
      type: "edit_done",
      formId: form!.id,
      summary: "Edit treatment: doseValue: 40",
    });
    expect(state.status).toBe("answered");
    expect(state.items.at(-1)).toMatchObject({ state: "submitted" });
  });
});
