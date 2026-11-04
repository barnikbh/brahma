import { describe, expect, it, vi } from "vitest";
import { ANSWER_EVENTS, apiError, installFakeApi, sseText, streamOf } from "@/test/fakeApi";
import { ApiError } from "./client";
import type { WalkEvent } from "./types";
import { CONNECTION_LOST, readSse, streamWalk, toWalkEvent } from "./walkStream";

async function collect(stream: ReadableStream<Uint8Array>) {
  const out = [];
  for await (const message of readSse(stream)) out.push(message);
  return out;
}

describe("SSE parsing", () => {
  it("joins events split across chunks, in order", async () => {
    const text = sseText(ANSWER_EVENTS);
    for (const size of [1, 7, 64, text.length]) {
      const messages = await collect(streamOf(text, size));
      expect(messages.map((m) => m.event)).toEqual(ANSWER_EVENTS.map((e) => e.type));
    }
  });

  it("handles multi-line data, CRLF line ends, comments and a final block without a blank line", async () => {
    const text =
      ': keep-alive\r\nevent: line\r\ndata: {"sectionId":"findings",\r\ndata: "text":"a","nodeIds":["N1"]}\r\n\r\nevent: progress\ndata: {"step":"refining"}';
    const messages = await collect(streamOf(text, 5));
    expect(messages).toHaveLength(2);
    expect(JSON.parse(messages[0].data)).toEqual({
      sectionId: "findings",
      text: "a",
      nodeIds: ["N1"],
    });
    expect(toWalkEvent(messages[1])).toEqual({ type: "progress", payload: { step: "refining" } });
  });

  it("ignores unknown events and bad JSON", () => {
    expect(toWalkEvent({ event: "message", data: "{}" })).toBeNull();
    expect(toWalkEvent({ event: "line", data: "not json" })).toBeNull();
  });
});

describe("streamWalk", () => {
  it("passes each event to the caller as it arrives", async () => {
    const fake = installFakeApi();
    fake.walkStreams.push(ANSWER_EVENTS);
    const seen: WalkEvent[] = [];
    await streamWalk("BR-000001", { mode: "continue", walkId: "wk-1" }, (e) => seen.push(e));
    expect(seen.map((e) => e.type)).toEqual(ANSWER_EVENTS.map((e) => e.type));
    const call = fake.callsTo("POST", "/api/cases/:id/walk")[0];
    expect(call.body).toEqual({ mode: "continue", walkId: "wk-1" });
    expect(call.headers["x-brahma-tab"]).toBeTruthy();
  });

  it("throws the C8 error before the stream opens (409 case_read_only)", async () => {
    installFakeApi({
      "POST /api/cases/:id/walk": () =>
        apiError(409, "case_read_only", "The case is open in another tab; this one is read-only."),
    });
    const onEvent = vi.fn();
    const error = await streamWalk("BR-000001", { mode: "start", text: "x" }, onEvent).catch(
      (e: unknown) => e,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ code: "case_read_only" });
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("reports a stream that drops without a closing event as a retryable error", async () => {
    const fake = installFakeApi();
    fake.walkStreams.push(ANSWER_EVENTS.slice(0, 3));
    const seen: WalkEvent[] = [];
    await streamWalk("BR-000001", { mode: "continue", walkId: "wk-1" }, (e) => seen.push(e));
    expect(seen.at(-1)).toEqual({
      type: "error",
      payload: { code: "connection_lost", message: CONNECTION_LOST, retryable: true },
    });
  });

  it("passes a review through and closes the stream without a connection error", async () => {
    const fake = installFakeApi();
    fake.walkStreams.push([
      { type: "progress", payload: { step: "reading_findings" } },
      {
        type: "reviewed",
        payload: { walkId: "wk-1", nodeId: "IBD-N81", met: false, text: "Review recorded" },
      },
    ]);
    const seen: WalkEvent[] = [];
    await streamWalk(
      "BR-000001",
      { mode: "review", walkId: "wk-1", branchNodeId: "IBD-N81", reviewValue: "20" },
      (e) => seen.push(e),
    );
    expect(seen.map((e) => e.type)).toEqual(["progress", "reviewed"]);
  });

  it("reports a stream that errors mid-way the same way", async () => {
    const encoder = new TextEncoder();
    let pulls = 0;
    const broken = new ReadableStream<Uint8Array>({
      pull(controller) {
        pulls += 1;
        if (pulls === 1) controller.enqueue(encoder.encode(sseText(ANSWER_EVENTS.slice(0, 1))));
        else controller.error(new TypeError("network"));
      },
    });
    installFakeApi({ "POST /api/cases/:id/walk": () => new Response(broken, { status: 200 }) });
    const seen: WalkEvent[] = [];
    await streamWalk("BR-000001", { mode: "continue", walkId: "wk-1" }, (e) => seen.push(e));
    expect(seen.map((e) => e.type)).toEqual(["progress", "error"]);
  });
});
