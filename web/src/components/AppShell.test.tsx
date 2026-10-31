import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { apiError, installFakeApi } from "@/test/fakeApi";
import { renderApp } from "@/test/render";

describe("AppShell", () => {
  it.each(["/patients", "/history", "/knowledge", "/signin"])(
    "shows the disclaimer and pack chips on %s",
    async (path) => {
      installFakeApi();
      renderApp(path);
      const bar = await screen.findByTestId("disclaimer-bar");
      expect(bar).toHaveTextContent("Decision support, not diagnosis.");
      await waitFor(() =>
        expect(screen.getAllByTestId("pack-chip").map((c) => c.textContent)).toEqual([
          "IBD v1.0",
          "URO v0.1",
        ]),
      );
    },
  );

  it("shows the server-not-running state with Retry", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    renderApp("/signin");
    // The shell banner, and the sign-in page's own load error, both say so.
    expect(await screen.findAllByText(/The Brahma server is not running/)).toHaveLength(2);
    installFakeApi();
    await userEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    await waitFor(() =>
      expect(screen.getAllByText(/The Brahma server is not running/)).toHaveLength(1),
    );
  });

  it("hides Knowledge when the feature is not mounted, and has the desktop-only notice", async () => {
    installFakeApi({ "GET /api/features": () => ({ features: [] }) });
    renderApp("/patients");
    await screen.findByRole("navigation", { name: "Main" });
    expect(screen.queryByRole("link", { name: "Knowledge" })).not.toBeInTheDocument();
    expect(screen.getByTestId("desktop-only")).toHaveTextContent(
      "Brahma is built for desktop screens (1280 px and up).",
    );
  });

  it("sends a signed-out visitor to sign-in", async () => {
    installFakeApi({
      "GET /api/session": () => apiError(401, "not_signed_in", "Sign in first."),
    });
    renderApp("/patients");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
  });

  it("signs out from the header", async () => {
    const fake = installFakeApi();
    renderApp("/patients");
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(fake.callsTo("DELETE", "/api/session")).toHaveLength(1);
  });
});
