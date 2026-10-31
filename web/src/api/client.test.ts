import { describe, expect, it, vi } from "vitest";
import { apiError, installFakeApi, json } from "@/test/fakeApi";
import {
  ApiError,
  TAB_HEADER,
  api,
  requestsInFlight,
  setUnauthorizedHandler,
  tabId,
  versionParam,
} from "./client";

describe("api client", () => {
  it("parses the C8 error shape into an ApiError", async () => {
    installFakeApi({
      "GET /api/cases/:id": () => apiError(404, "case_not_found", "No case BR-404.", false),
    });
    const error = await api.getCase("BR-404").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 404,
      code: "case_not_found",
      message: "No case BR-404.",
    });
  });

  it("parses a C9 error without retryable, and a non-JSON 500 as retryable", async () => {
    const fake = installFakeApi({
      "POST /api/knowledge/proposals": () =>
        json({ error: { code: "CopyFlagged", message: "Copy flag set." } }, 409),
    });
    const flagged = await api
      .createProposal({ pack: "IBD", nodeId: "IBD-N1", change: { label: "x" }, comment: "c" })
      .catch((e: unknown) => e);
    expect(flagged).toMatchObject({ status: 409, code: "CopyFlagged", retryable: false });
    fake.on("GET /api/health", () => new Response("oops", { status: 500 }));
    const broken = await api.health().catch((e: unknown) => e);
    expect(broken).toMatchObject({ status: 500, code: "http_500", retryable: true });
  });

  it("sends the tab header and same-origin credentials on every request", async () => {
    const fake = installFakeApi();
    await api.lock("BR-000001");
    const call = fake.callsTo("POST", "/api/cases/:id/lock")[0];
    expect(call.headers[TAB_HEADER.toLowerCase()]).toBe(tabId());
    expect(call.body).toEqual({ tabId: tabId() });
    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe("same-origin");
    expect(tabId()).toBe(tabId()); // stable for the tab
  });

  it("calls the unauthorized handler on a 401", async () => {
    installFakeApi({
      "GET /api/session": () =>
        apiError(401, "not_signed_in", "Sign in with a demo profile first."),
    });
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    await expect(api.session()).rejects.toMatchObject({ status: 401, code: "not_signed_in" });
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("reports a stopped server as a retryable server_unreachable error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.health()).rejects.toMatchObject({
      status: 0,
      code: "server_unreachable",
      retryable: true,
    });
    expect(requestsInFlight()).toBe(0);
  });

  it("builds query strings and version parameters", async () => {
    const fake = installFakeApi();
    await api.sessions({ outcome: "answered", q: " colitis " });
    await api.node("IBD 1.0", "IBD-N51", "BR-000001");
    await api.searchPatients("BR 1");
    expect(fake.calls.map((c) => c.url)).toEqual([
      "/api/sessions?outcome=answered&q=colitis",
      "/api/nodes/IBD%401.0/IBD-N51?caseId=BR-000001",
      "/api/patients?q=BR%201",
    ]);
    expect(versionParam("URO 0.1")).toBe("URO@0.1");
    expect(api.exportUrl("s-1", "pdf")).toBe("/api/sessions/s-1/export?format=pdf");
  });
});
