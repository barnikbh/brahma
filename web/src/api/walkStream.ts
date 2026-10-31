// The walk as Server-Sent Events over fetch + ReadableStream (C8, NFR1.5).
// Each event is handed to the caller as soon as its block is complete: no batching.

import { apiHeaders, errorFrom, networkError, tracked } from "./client";
import type { WalkEvent, WalkEventType, WalkRequest } from "./types";

export interface SseMessage {
  event: string;
  data: string;
}

const KNOWN: ReadonlySet<WalkEventType> = new Set<WalkEventType>([
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
]);

/** Parse one SSE block ("event: x\ndata: {...}") into a message, or null for a comment. */
function parseBlock(block: string): SseMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const raw of block.split("\n")) {
    if (!raw || raw.startsWith(":")) continue;
    const colon = raw.indexOf(":");
    const field = colon === -1 ? raw : raw.slice(0, colon);
    let value = colon === -1 ? "" : raw.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  if (data.length === 0) return null;
  return { event, data: data.join("\n") };
}

/** Yield SSE messages from a byte stream, across chunk boundaries and CRLF line ends. */
export async function* readSse(stream: ReadableStream<Uint8Array>): AsyncGenerator<SseMessage> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n?/g, "\n");
      let end = buffer.indexOf("\n\n");
      while (end !== -1) {
        const message = parseBlock(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        if (message) yield message;
        end = buffer.indexOf("\n\n");
      }
    }
    buffer += decoder.decode();
    const last = parseBlock(buffer.replace(/\r\n?/g, "\n").trim());
    if (last) yield last;
  } finally {
    reader.releaseLock();
  }
}

/** A typed walk event from an SSE message, or null when it is not a C8 walk event. */
export function toWalkEvent(message: SseMessage): WalkEvent | null {
  if (!KNOWN.has(message.event as WalkEventType)) return null;
  try {
    const payload = JSON.parse(message.data) as unknown;
    if (typeof payload !== "object" || payload === null) return null;
    return { type: message.event, payload } as WalkEvent;
  } catch {
    return null;
  }
}

export const CONNECTION_LOST = "The connection to the server dropped. Your entries are kept.";
const TERMINAL: ReadonlySet<WalkEventType> = new Set(["done", "paused", "error", "lane_closed"]);

/**
 * POST a walk request and pass each event to `onEvent` as it arrives. HTTP errors (401,
 * 404, 409 case_read_only) and network failures throw an ApiError before any event. A
 * stream that ends without a closing event is reported as a retryable `error` event.
 */
export function streamWalk(
  caseId: string,
  body: WalkRequest,
  onEvent: (event: WalkEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return tracked(() => runWalk(caseId, body, onEvent, signal));
}

async function runWalk(
  caseId: string,
  body: WalkRequest,
  onEvent: (event: WalkEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/cases/${encodeURIComponent(caseId)}/walk`, {
      method: "POST",
      credentials: "same-origin",
      headers: { ...apiHeaders(true), Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw networkError();
  }
  if (!response.ok) throw await errorFrom(response);
  if (!response.body) throw networkError();
  let closed = false;
  try {
    for await (const message of readSse(response.body)) {
      const event = toWalkEvent(message);
      if (!event) continue;
      // An explore stream ends with its lane's section_done (there is no done event).
      if (TERMINAL.has(event.type) || (event.type === "section_done" && event.payload.laneId))
        closed = true;
      onEvent(event);
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    closed = false;
  }
  if (!closed) {
    onEvent({
      type: "error",
      payload: { code: "connection_lost", message: CONNECTION_LOST, retryable: true },
    });
  }
}
