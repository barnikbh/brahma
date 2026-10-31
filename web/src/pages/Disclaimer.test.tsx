import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, installFakeApi, sessionView } from "@/test/fakeApi";
import { renderApp } from "@/test/render";

describe("DisclaimerPage", () => {
  it("keeps Accept disabled until both boxes are ticked, then lands on Patients", async () => {
    const fake = installFakeApi({ "GET /api/session": () => sessionView(undefined, true) });
    renderApp("/patients"); // redirected to the disclaimer first
    const accept = await screen.findByRole("button", { name: "Accept and continue" });
    expect(accept).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /decision support/i }));
    expect(accept).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox", { name: /synthetic cases only/i }));
    expect(accept).toBeEnabled();
    await userEvent.click(accept);
    expect(await screen.findByRole("heading", { name: "Patients" })).toBeInTheDocument();
    expect(fake.callsTo("POST", "/api/disclaimer")).toHaveLength(1);
  });

  it("shows a save failure and offers Retry", async () => {
    installFakeApi({
      "GET /api/session": () => sessionView(undefined, true),
      "POST /api/disclaimer": () => apiError(500, "x", "Acceptance failed to save.", true),
    });
    renderApp("/disclaimer");
    await userEvent.click(await screen.findByRole("checkbox", { name: /decision support/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /synthetic cases only/i }));
    await userEvent.click(screen.getByRole("button", { name: "Accept and continue" }));
    expect(await screen.findByText("Acceptance failed to save.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });
});
