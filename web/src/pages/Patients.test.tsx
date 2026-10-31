import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { apiError, caseView, installFakeApi } from "@/test/fakeApi";
import { renderApp } from "@/test/render";

describe("PatientsPage", () => {
  it("lists recent saved patients before anything is typed", async () => {
    installFakeApi({
      "GET /api/patients": () => ({
        results: [
          {
            caseId: "BR-000009",
            patientId: "pt-9",
            syntheticName: "Demo Patient Z",
            status: "plan_in_place",
            updatedAt: "2026-10-31T08:00:00Z",
          },
        ],
        query: "",
      }),
    });
    renderApp("/patients");
    expect(await screen.findByText("Recent patients")).toBeInTheDocument();
    expect(screen.getByText("BR-000009")).toBeInTheDocument();
  });

  it("shows No patients found and Create for an empty search", async () => {
    const fake = installFakeApi();
    renderApp("/patients");
    await userEvent.type(await screen.findByLabelText(/Search by case ID/), "headache");
    expect(await screen.findByText("No patients found")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Create new patient" })).toHaveLength(2);
    // Debounced: one request for the whole word.
    expect(fake.callsTo("GET", "/api/patients")).toHaveLength(1);
  });

  it("lists matches with a status chip and the synthetic label, and opens one", async () => {
    installFakeApi({
      "GET /api/patients": () => ({
        results: [
          {
            caseId: "BR-000001",
            patientId: "pt-1",
            syntheticName: "Demo Patient A",
            status: "needs_data",
            updatedAt: "2026-10-30T10:00:00Z",
          },
        ],
        query: "BR",
      }),
    });
    renderApp("/patients");
    await userEvent.type(await screen.findByLabelText(/Search by case ID/), "BR");
    const row = await screen.findByRole("button", { name: /Demo Patient A/ });
    expect(row).toHaveTextContent("synthetic");
    expect(row).toHaveTextContent("? Needs data");
    await userEvent.click(row);
    expect(await screen.findByText("Consultation chat")).toBeInTheDocument();
  });

  it("creates a synthetic patient and opens the workspace; keeps input on error", async () => {
    const fake = installFakeApi({
      "POST /api/patients": () =>
        apiError(422, "invalid_request", "These fields are not valid: age."),
    });
    renderApp("/patients");
    await userEvent.click(await screen.findByRole("button", { name: "Create new patient" }));
    await userEvent.type(screen.getByLabelText("Synthetic name"), "Demo Patient B");
    await userEvent.type(screen.getByLabelText("Age (years)"), "41");
    await userEvent.type(screen.getByLabelText("Allergies (comma separated)"), "penicillin, latex");
    await userEvent.click(screen.getByRole("button", { name: "Create and open" }));
    expect(await screen.findByText(/These fields are not valid: age./)).toBeInTheDocument();
    expect(screen.getByLabelText("Synthetic name")).toHaveValue("Demo Patient B");
    fake.on("POST /api/patients", () => caseView());
    await userEvent.click(screen.getByRole("button", { name: "Create and open" }));
    await waitFor(() => expect(screen.getByText("Consultation chat")).toBeInTheDocument());
    expect(fake.callsTo("POST", "/api/patients")[1].body).toMatchObject({
      syntheticName: "Demo Patient B",
      age: 41,
      sex: "female",
      allergies: ["penicillin", "latex"],
    });
  });
});
