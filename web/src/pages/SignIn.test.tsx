import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, installFakeApi, sessionView } from "@/test/fakeApi";
import { renderApp } from "@/test/render";

describe("SignInPage", () => {
  it("lands on Patients after signing in when the disclaimer is accepted", async () => {
    installFakeApi({
      "GET /api/session": () => apiError(401, "not_signed_in", "Sign in first."),
      "POST /api/session": () => sessionView(),
    });
    renderApp("/signin");
    await userEvent.click(await screen.findByRole("button", { name: /Dr\. Maya/ }));
    expect(await screen.findByRole("heading", { name: "Patients" })).toBeInTheDocument();
    expect(screen.getByTestId("profile-name")).toHaveTextContent("Dr. Maya (demo)");
  });

  it("goes to the disclaimer on first sign-in", async () => {
    installFakeApi({ "GET /api/session": () => apiError(401, "not_signed_in", "Sign in first.") });
    renderApp("/signin");
    await userEvent.click(await screen.findByRole("button", { name: /Dr\. Maya/ }));
    expect(
      await screen.findByRole("heading", { name: "Decision support, not diagnosis" }),
    ).toBeInTheDocument();
  });

  it("shows a load failure with Retry", async () => {
    const fake = installFakeApi({
      "GET /api/session": () => apiError(401, "not_signed_in", "Sign in first."),
      "GET /api/profiles": () => apiError(500, "boom", "Profiles failed to load."),
    });
    renderApp("/signin");
    expect(await screen.findByText("Profiles failed to load.")).toBeInTheDocument();
    fake.on("GET /api/profiles", () => ({ profiles: [] }));
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(screen.queryByText("Profiles failed to load.")).not.toBeInTheDocument();
  });
});
