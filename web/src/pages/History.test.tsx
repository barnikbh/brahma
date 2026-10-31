import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { installFakeApi } from "@/test/fakeApi";
import { renderApp } from "@/test/render";

describe("HistoryPage", () => {
  it("shows the empty state for no sessions and for filters with no match", async () => {
    const fake = installFakeApi({ "GET /api/sessions": () => ({ sessions: [] }) });
    renderApp("/history");
    expect(await screen.findByText("No sessions yet")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Outcome"), "out_of_knowledge");
    expect(await screen.findByText("No sessions match these filters")).toBeInTheDocument();
    await waitFor(() =>
      expect(fake.calls.some((c) => c.url === "/api/sessions?outcome=out_of_knowledge")).toBe(true),
    );
  });

  it("opens a session: inputs, answer, why with chips, read-only replay and export", async () => {
    renderApp("/history");
    installFakeApi();
    await userEvent.click(await screen.findByRole("button", { name: /s-1/ }));
    const detail = await screen.findByRole("article", { name: "Session s-1" });
    expect(detail).toHaveTextContent("Ulcerative colitis → Acute severe UC");
    expect(detail).toHaveTextContent("Bloody diarrhoea pointed to IBD.");
    expect(within(detail).getByText(/read-only replay/)).toBeInTheDocument();
    expect(within(detail).getByRole("link", { name: "Export JSON" })).toHaveAttribute(
      "href",
      "/api/sessions/s-1/export?format=json",
    );
    expect(within(detail).getByRole("link", { name: "Export PDF" })).toHaveAttribute(
      "href",
      "/api/sessions/s-1/export?format=pdf",
    );
    expect(detail).toHaveTextContent("session_recorded");
    // Replay is read-only: no chat, no composer, no edit actions.
    expect(screen.queryByRole("textbox", { name: /Message the agent/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit treatment" })).not.toBeInTheDocument();
  });
});
