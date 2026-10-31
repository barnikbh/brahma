// Typed fetch wrapper for the local U4 server (C8) and the knowledge API (C9).
// - same-origin cookies only (the signed session cookie is HttpOnly)
// - every error body {error: {code, message, retryable}} becomes an ApiError
// - the tab ID in sessionStorage is sent as X-Brahma-Tab (case lock, BR4.3)
// - a 401 sends the user to sign-in

import type {
  ApiErrorBody,
  CaseSummary,
  CaseView,
  EditOutcome,
  Feature,
  Health,
  LockState,
  MapData,
  NewPatient,
  NodeComment,
  NodeDetail,
  Outcome,
  PatientChange,
  Profile,
  PackGraph,
  PackInfo,
  Proposal,
  ProposalIn,
  BrowseDetail,
  UpdateThread,
  SessionDetail,
  SessionSummary,
  SessionView,
  VersionHistoryEntry,
} from "./types";

export const TAB_HEADER = "X-Brahma-Tab";
const TAB_KEY = "brahma.tabId";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;

  constructor(status: number, code: string, message: string, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

/** This tab's ID, created once per tab and kept in sessionStorage. */
export function tabId(): string {
  let id: string | null = null;
  try {
    id = sessionStorage.getItem(TAB_KEY);
  } catch {
    id = null;
  }
  if (!id) {
    id = `tab-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
    try {
      sessionStorage.setItem(TAB_KEY, id);
    } catch {
      // sessionStorage unavailable: the ID lives for this page only
    }
  }
  return id;
}

type UnauthorizedHandler = () => void;

let onUnauthorized: UnauthorizedHandler = () => {
  if (window.location.pathname !== "/signin") window.location.assign("/signin");
};

/** The app replaces the default full-page redirect with a router navigation. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  onUnauthorized = handler;
}

export function apiHeaders(json: boolean): Record<string, string> {
  const headers: Record<string, string> = { [TAB_HEADER]: tabId(), Accept: "application/json" };
  if (json) headers["Content-Type"] = "application/json";
  return headers;
}

/** Turn a non-OK response into an ApiError (and handle 401). */
export async function errorFrom(response: Response): Promise<ApiError> {
  let code = `http_${response.status}`;
  let message = "The server could not complete this request.";
  let retryable = response.status >= 500;
  try {
    const body = (await response.json()) as Partial<ApiErrorBody>;
    if (body && body.error && typeof body.error.message === "string") {
      code = String(body.error.code ?? code);
      message = body.error.message;
      retryable = Boolean(body.error.retryable);
    }
  } catch {
    // not JSON: keep the generic message
  }
  if (response.status === 401) onUnauthorized();
  return new ApiError(response.status, code, message, retryable);
}

export const SERVER_DOWN_MESSAGE =
  "The Brahma server is not running. Start it with `python -m brahma.server`, then retry.";

/** A network failure (server stopped) as an ApiError. */
export function networkError(): ApiError {
  return new ApiError(0, "server_unreachable", SERVER_DOWN_MESSAGE, true);
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  keepalive?: boolean;
}

// Requests in flight. The U4 server shares one SQLite connection across worker threads,
// so background traffic (the lock heartbeat) waits until nothing else is running.
let inFlight = 0;

export function requestsInFlight(): number {
  return inFlight;
}

/** Run `work` counted as an in-flight request. */
export async function tracked<T>(work: () => Promise<T>): Promise<T> {
  inFlight += 1;
  try {
    return await work();
  } finally {
    inFlight -= 1;
  }
}

export function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return tracked(() => send<T>(path, options));
}

async function send<T>(path: string, options: RequestOptions): Promise<T> {
  const hasBody = options.body !== undefined;
  let response: Response;
  try {
    response = await fetch(path, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      headers: apiHeaders(hasBody),
      body: hasBody ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
      keepalive: options.keepalive,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw networkError();
  }
  if (!response.ok) throw await errorFrom(response);
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

const enc = encodeURIComponent;

/** "IBD 1.0" (as the map and case labels read) to the "IBD@1.0" node-route form. */
export function versionParam(label: string): string {
  return label.trim().replace(/[ -]/, "@");
}

export const api = {
  profiles: () => request<{ profiles: Profile[] }>("/api/profiles"),
  signIn: (profileId: string) =>
    request<SessionView>("/api/session", { method: "POST", body: { profileId } }),
  session: () => request<SessionView>("/api/session"),
  signOut: () => request<void>("/api/session", { method: "DELETE" }),
  acceptDisclaimer: () =>
    request<{ acceptanceId: string; packVersions: string; disclaimer: string }>("/api/disclaimer", {
      method: "POST",
    }),
  features: () => request<{ features: Feature[] }>("/api/features"),
  health: () => request<Health>("/api/health"),

  searchPatients: (q: string, signal?: AbortSignal) =>
    request<{ results: CaseSummary[]; query: string }>(`/api/patients?q=${enc(q)}`, { signal }),
  createPatient: (patient: NewPatient) =>
    request<CaseView>("/api/patients", { method: "POST", body: patient }),
  getCase: (caseId: string) => request<CaseView>(`/api/cases/${enc(caseId)}`),
  lock: (caseId: string) =>
    request<{ state: LockState }>(`/api/cases/${enc(caseId)}/lock`, {
      method: "POST",
      body: { tabId: tabId() },
    }),
  unlock: (caseId: string) =>
    request<void>(`/api/cases/${enc(caseId)}/lock`, {
      method: "DELETE",
      body: { tabId: tabId() },
      keepalive: true,
    }),
  sendMessage: (caseId: string, text: string) =>
    request<{ messageId: string; offers: string[] }>(`/api/cases/${enc(caseId)}/messages`, {
      method: "POST",
      body: { text },
    }),
  changePatient: (caseId: string, change: PatientChange) =>
    request<CaseView>(`/api/cases/${enc(caseId)}/patient`, { method: "PATCH", body: change }),
  saveDraft: (caseId: string, messageId: string, values: Record<string, unknown>) =>
    request<void>(`/api/cases/${enc(caseId)}/forms/${enc(messageId)}/draft`, {
      method: "PUT",
      body: values,
    }),
  treatmentEdit: (caseId: string, nodeId: string, newValues: Record<string, unknown>) =>
    request<EditOutcome>(`/api/cases/${enc(caseId)}/treatment-edits`, {
      method: "POST",
      body: { nodeId, newValues },
    }),
  caseMap: (caseId: string, params: { walkId?: string; sessionId?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.walkId) query.set("walkId", params.walkId);
    if (params.sessionId) query.set("sessionId", params.sessionId);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<MapData>(`/api/cases/${enc(caseId)}/map${suffix}`);
  },

  node: (version: string, nodeId: string, caseId?: string) =>
    request<NodeDetail>(
      `/api/nodes/${enc(versionParam(version))}/${enc(nodeId)}${caseId ? `?caseId=${enc(caseId)}` : ""}`,
    ),
  addComment: (version: string, nodeId: string, text: string) =>
    request<NodeComment>(`/api/nodes/${enc(versionParam(version))}/${enc(nodeId)}/comments`, {
      method: "POST",
      body: { text },
    }),

  sessions: (filter: { outcome?: Outcome | ""; q?: string } = {}) => {
    const query = new URLSearchParams();
    if (filter.outcome) query.set("outcome", filter.outcome);
    if (filter.q && filter.q.trim()) query.set("q", filter.q.trim());
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request<{ sessions: SessionSummary[] }>(`/api/sessions${suffix}`);
  },
  sessionDetail: (sessionId: string) => request<SessionDetail>(`/api/sessions/${enc(sessionId)}`),
  exportUrl: (sessionId: string, format: "json" | "pdf") =>
    `/api/sessions/${enc(sessionId)}/export?format=${format}`,

  proposals: () => request<{ proposals: Proposal[] }>("/api/knowledge/proposals"),
  proposal: (id: string) => request<Proposal>(`/api/knowledge/proposals/${enc(id)}`),
  createProposal: (proposal: ProposalIn) =>
    request<Proposal>("/api/knowledge/proposals", { method: "POST", body: proposal }),
  publish: (id: string, comment: string) =>
    request<Proposal>(`/api/knowledge/proposals/${enc(id)}/publish`, {
      method: "POST",
      body: { comment: comment || null },
    }),
  reject: (id: string, comment: string) =>
    request<Proposal>(`/api/knowledge/proposals/${enc(id)}/reject`, {
      method: "POST",
      body: { comment },
    }),
  packs: () => request<{ packs: PackInfo[] }>("/api/knowledge/packs"),
  graph: (pack: string, version?: string) =>
    request<PackGraph>(
      `/api/knowledge/graph?pack=${enc(pack)}${version ? `&version=${enc(version)}` : ""}`,
    ),
  browseNode: (nodeId: string, pack: string, version?: string) =>
    request<BrowseDetail>(
      `/api/knowledge/nodes/${enc(nodeId)}?pack=${enc(pack)}${version ? `&version=${enc(version)}` : ""}`,
    ),
  updateThreads: () => request<{ threads: UpdateThread[] }>("/api/knowledge/updates"),
  sendUpdate: (body: { text: string; threadId?: string | null; pack: string }) =>
    request<UpdateThread>("/api/knowledge/updates", { method: "POST", body }),
  versions: (pack: string) =>
    request<{ pack: string; versions: VersionHistoryEntry[] }>(
      `/api/knowledge/versions?pack=${enc(pack)}`,
    ),
};
