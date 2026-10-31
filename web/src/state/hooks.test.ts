import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ANSWER_EVENTS, START_EVENTS, apiError, caseView, installFakeApi } from "@/test/fakeApi";
import { useCase } from "./useCase";
import { HEARTBEAT_MS, useLock } from "./useLock";

describe("useLock", () => {
  it("heartbeats every 15 s and releases on unload and unmount", async () => {
    vi.useFakeTimers();
    const fake = installFakeApi();
    const { result, unmount } = renderHook(() => useLock("BR-000001"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current).toBe("held");
    expect(fake.callsTo("POST", "/api/cases/:id/lock")).toHaveLength(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(HEARTBEAT_MS * 2);
    });
    expect(fake.callsTo("POST", "/api/cases/:id/lock")).toHaveLength(3);
    window.dispatchEvent(new Event("beforeunload"));
    expect(fake.callsTo("DELETE", "/api/cases/:id/lock")).toHaveLength(1);
    unmount();
    expect(fake.callsTo("DELETE", "/api/cases/:id/lock")).toHaveLength(2);
  });

  it("returns read_only when another tab holds the case", async () => {
    installFakeApi({ "POST /api/cases/:id/lock": () => ({ state: "read_only" }) });
    const { result } = renderHook(() => useLock("BR-000001"));
    await waitFor(() => expect(result.current).toBe("read_only"));
  });

  it("waits until enabled", () => {
    const fake = installFakeApi();
    renderHook(() => useLock("BR-000001", false));
    expect(fake.calls).toHaveLength(0);
  });
});

describe("useCase", () => {
  it("loads the case and streams a walk into the reducer", async () => {
    const fake = installFakeApi();
    fake.walkStreams.push(START_EVENTS, ANSWER_EVENTS);
    const { result } = renderHook(() => useCase("BR-000001"));
    await waitFor(() => expect(result.current.view?.case.caseId).toBe("BR-000001"));
    await act(() => result.current.walk({ mode: "start", text: "case text" }));
    expect(result.current.state.status).toBe("confirm");
    await act(() => result.current.walk({ mode: "continue", walkId: "wk-1" }));
    expect(result.current.state.status).toBe("answered");
  });

  it("turns an HTTP error into the error state and a load error into loadError", async () => {
    const fake = installFakeApi({
      "POST /api/cases/:id/walk": () => apiError(503, "busy", "The server is busy.", true),
    });
    const { result } = renderHook(() => useCase("BR-000001"));
    await waitFor(() => expect(result.current.view).not.toBeNull());
    await act(() => result.current.walk({ mode: "start", text: "case text" }));
    expect(result.current.state.status).toBe("error");
    expect(result.current.state.error?.message).toBe("The server is busy.");
    fake.on("GET /api/cases/:id", () => apiError(404, "case_not_found", "No such case."));
    await act(() => result.current.reload());
    expect(result.current.loadError?.code).toBe("case_not_found");
  });

  it("loads the map of a case that has a walk", async () => {
    const fake = installFakeApi({
      "GET /api/cases/:id": () =>
        caseView({
          walk: {
            walkId: "wk-1",
            status: "answered",
            waitingFor: null,
            lastSectionDone: 8,
            counts: { steps: 2, cited: 1, ungrounded: 0 },
            packVersion: "IBD 1.0",
          },
        }),
    });
    const { result } = renderHook(() => useCase("BR-000001"));
    await waitFor(() => expect(fake.callsTo("GET", "/api/cases/:id/map")).toHaveLength(1));
    await waitFor(() => expect(result.current.state.map.version).toBe("IBD 1.0"));
  });
});
