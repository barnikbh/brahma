import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { MapNode, WalkEvent } from "@/api/types";
import {
  ANSWER_EVENTS,
  DEMO_TEXT,
  FOLLOW_UP_EVENTS,
  FOLLOW_UP_TEXT,
  NEEDS_DATA_EVENTS,
  START_EVENTS,
  apiError,
  caseView,
  installFakeApi,
} from "@/test/fakeApi";
import { renderApp } from "@/test/render";

async function walkDemo() {
  const fake = installFakeApi();
  fake.walkStreams.push(START_EVENTS, NEEDS_DATA_EVENTS, ANSWER_EVENTS);
  renderApp("/cases/BR-000001");
  await userEvent.type(await screen.findByLabelText(/Describe the patient/), DEMO_TEXT);
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
  const confirm = await screen.findByRole("form", { name: "Confirm findings" });
  expect(within(confirm).getByText("Hb 10.2")).toBeInTheDocument();
  await userEvent.click(within(confirm).getByRole("button", { name: /Looks right/ }));
  const needs = await screen.findByRole("form", { name: "Needs more data" });
  await userEvent.selectOptions(within(needs).getByLabelText(/Stool culture/), "negative");
  await userEvent.click(within(needs).getByRole("button", { name: "Submit results" }));
  await screen.findByTestId("walk-summary");
  return fake;
}

describe("WorkspacePage", () => {
  it("reads chat after a finished walk as treatment history and answers at once", async () => {
    const fake = await walkDemo();
    fake.walkStreams.push(FOLLOW_UP_EVENTS);
    await userEvent.type(screen.getByLabelText(/Message the agent/), FOLLOW_UP_TEXT);
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(
      await screen.findByText(
        "Noted treatment history: infliximab — no response; corticosteroid — responded.",
      ),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /90 mg under the skin/ })).toBeInTheDocument();
    expect(screen.queryByText(/Review findings and re-walk/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Noted\. Use/)).not.toBeInTheDocument();
    expect(fake.callsTo("POST", "/api/cases/:id/messages")).toHaveLength(0);
    const walks = fake.callsTo("POST", "/api/cases/:id/walk").map((c) => c.body);
    expect(walks.at(-1)).toEqual({ mode: "follow_up", text: FOLLOW_UP_TEXT });
    await waitFor(() =>
      expect(document.querySelector('[data-map-node="IBD-N53"]')).toHaveTextContent(
        "Tried · failed",
      ),
    );
    expect(screen.getAllByTestId("walk-summary")).toHaveLength(2);
  });

  it("sends the follow-up with Enter in the composer", async () => {
    const fake = await walkDemo();
    fake.walkStreams.push(FOLLOW_UP_EVENTS);
    await userEvent.type(screen.getByLabelText(/Message the agent/), FOLLOW_UP_TEXT);
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByText(
        "Noted treatment history: infliximab — no response; corticosteroid — responded.",
      ),
    ).toBeInTheDocument();
    const walks = fake.callsTo("POST", "/api/cases/:id/walk").map((c) => c.body);
    expect(walks.at(-1)).toEqual({ mode: "follow_up", text: FOLLOW_UP_TEXT });
  });

  it("walks the demo: confirm form, needs-data form, cited lines and 0 ungrounded", async () => {
    const fake = await walkDemo();
    expect(screen.getByText(/Confirmed findings: age 34 years/)).toBeInTheDocument();
    expect(screen.getByText(/Results: Stool culture: negative · Ileocolonoscopy: not yet tested/));
    const line = screen.getByRole("button", { name: /Visible blood in loose stools/ });
    expect(within(line).getByText("IBD-N1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Treatment tiers" })).toBeInTheDocument();
    const summary = screen.getByTestId("walk-summary");
    expect(summary).toHaveTextContent("0 ungrounded");
    expect(summary).toHaveTextContent("✓ 3 cited");
    expect(summary).toHaveTextContent("Decision support, not diagnosis");
    expect(summary).toHaveTextContent("Model: recorded");
    const walks = fake.callsTo("POST", "/api/cases/:id/walk");
    expect(walks.map((c) => c.body)).toEqual([
      { mode: "start", text: DEMO_TEXT },
      {
        mode: "continue",
        walkId: "wk-1",
        formMessageId: "msg-1",
        formValues: {
          findings: [
            { kind: "age", name: "age", value: 34, unit: "years", duration: null },
            {
              kind: "symptom",
              name: "bloody stool",
              value: null,
              unit: null,
              duration: "6 months",
            },
            { kind: "metric", name: "Hb", value: 10.2, unit: "g/dL", duration: null },
          ],
        },
      },
      {
        mode: "continue",
        walkId: "wk-1",
        formMessageId: "msg-2",
        formValues: { "IBD-N20": "negative" },
      },
    ]);
  });

  it("selecting a line opens its node panel; selecting a node highlights its line", async () => {
    await walkDemo();
    const line = screen.getByRole("button", { name: /Visible blood in loose stools/ });
    await userEvent.click(line);
    expect(line).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByTestId("node-panel")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close node detail" }));
    const node = document.querySelector<HTMLElement>('[data-map-node="IBD-N51"]')!;
    await userEvent.click(node);
    const treatment = screen.getByRole("button", { name: /Intravenous hydrocortisone/ });
    expect(treatment).toHaveAttribute("aria-pressed", "true");
    expect(line).toHaveAttribute("aria-pressed", "false");
  });

  it("selects with the keyboard: Enter on a line, Escape closes the panel", async () => {
    await walkDemo();
    const line = screen.getByRole("button", { name: /haemoglobin below 10.5/ });
    line.focus();
    await userEvent.keyboard("{Enter}");
    expect(line).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByTestId("node-panel")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("node-panel")).not.toBeInTheDocument());
  });

  it("shows the newer-version banner and re-walks on it", async () => {
    const fake = installFakeApi({
      "GET /api/cases/:id": () => caseView({ pinnedVersion: "IBD 1.0", newerVersion: "IBD 1.1" }),
    });
    renderApp("/cases/BR-000001");
    expect(
      await screen.findByText(/Newer version IBD 1.1 available: re-walk\? This case used IBD 1.0/),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Re-walk on IBD 1.1" }));
    expect(fake.callsTo("POST", "/api/cases/:id/walk")[0].body).toEqual({ mode: "rewalk" });
  });

  it("shows the read-only banner and disables input in a second tab", async () => {
    installFakeApi({
      "GET /api/cases/:id": () => caseView({ lock: "read_only" }),
      "POST /api/cases/:id/lock": () => ({ state: "read_only" }),
    });
    renderApp("/cases/BR-000001");
    expect(
      await screen.findByText("This case is open in another tab. This view is read-only."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: /Describe the patient|Message the agent/ }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Edit details" })).toBeDisabled();
  });

  it("offers Retry on error, keeping the inputs, and retries with the walkId", async () => {
    const failure: WalkEvent[] = [
      { type: "progress", payload: { step: "matching_diagnosis" } },
      {
        type: "error",
        payload: {
          code: "model_timeout",
          message: "The model provider did not answer in time.",
          retryable: true,
          walkId: "wk-1",
        },
      },
    ];
    const fake = installFakeApi();
    fake.walkStreams.push(START_EVENTS, failure, ANSWER_EVENTS);
    renderApp("/cases/BR-000001");
    await userEvent.type(await screen.findByLabelText(/Describe the patient/), DEMO_TEXT);
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await userEvent.click(await screen.findByRole("button", { name: /Looks right/ }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The model provider did not answer in time.");
    expect(screen.getByText(DEMO_TEXT)).toBeInTheDocument();
    expect(screen.getByRole("form", { name: "Confirm findings" })).toBeInTheDocument();
    await userEvent.click(within(alert).getByRole("button", { name: "Retry" }));
    await screen.findByTestId("walk-summary");
    expect(fake.callsTo("POST", "/api/cases/:id/walk")[2].body).toEqual({
      mode: "continue",
      walkId: "wk-1",
    });
  });

  it("shows out of knowledge with No grounded answer and Suggest adding this branch", async () => {
    const fake = installFakeApi();
    fake.walkStreams.push([
      { type: "map_update", payload: { walkId: "wk-9", nodes: [], edges: [] } },
      {
        type: "done",
        payload: {
          walkId: "wk-9",
          sessionId: "s-9",
          outcome: "out_of_knowledge",
          counts: { steps: 0, cited: 0, ungrounded: 0 },
          packVersion: "IBD 1.0",
          provider: "recorded",
          model: "recorded",
          disclaimer: "Decision support, not diagnosis",
          message: "No grounded answer",
          offers: ["suggest_branch"],
        },
      },
    ]);
    renderApp("/cases/BR-000001");
    await userEvent.type(
      await screen.findByLabelText(/Describe the patient/),
      "headache with aura",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    const summary = await screen.findByTestId("walk-summary");
    expect(summary).toHaveTextContent("⊘ No grounded answer");
    await userEvent.click(
      within(summary).getByRole("button", { name: "Suggest adding this branch" }),
    );
    expect(await screen.findByRole("heading", { name: "Knowledge update" })).toBeInTheDocument();
  });

  it("renders model-looking markup in a line as plain text (XSS)", async () => {
    const fake = installFakeApi();
    fake.walkStreams.push([
      {
        type: "line",
        payload: {
          sectionId: "findings",
          text: '<script>alert("x")</script><img src=x onerror=alert(1)>',
          nodeIds: ["IBD-N1"],
        },
      },
      ...ANSWER_EVENTS.slice(-1),
    ]);
    renderApp("/cases/BR-000001");
    await userEvent.type(await screen.findByLabelText(/Describe the patient/), "case");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText('<script>alert("x")</script><img src=x onerror=alert(1)>'));
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
  });

  it("shows a case that fails to load with Retry", async () => {
    installFakeApi({
      "GET /api/cases/:id": () => apiError(404, "case_not_found", "No case BR-000404."),
    });
    renderApp("/cases/BR-000404");
    expect(await screen.findByText("No case BR-000404.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("applies a treatment edit from the panel and marks the field edited", async () => {
    const fake = await walkDemo();
    fake.on("POST /api/cases/:id/treatment-edits", () => ({
      edit: {
        editId: "te-1",
        caseId: "BR-000001",
        nodeId: "IBD-N51",
        original: { frequency: "four times daily" },
        newValues: { frequency: "three times daily" },
        editorProfileId: "p-maya",
        createdAt: "t",
      },
      dose: { value: 100, unit: "mg", formula: "100 mg (fixed dose)" },
      safety: [],
    }));
    await userEvent.click(document.querySelector<HTMLElement>('[data-map-node="IBD-N51"]')!);
    await userEvent.click(await screen.findByRole("button", { name: "Edit treatment" }));
    const form = screen.getByRole("form", { name: "Edit treatment" });
    const frequency = within(form).getByLabelText("Frequency");
    await userEvent.clear(frequency);
    await userEvent.type(frequency, "three times daily");
    await userEvent.click(within(form).getByRole("button", { name: "Apply" }));
    expect(await screen.findByText(/✎ Edited by Dr. Maya/)).toBeInTheDocument();
    expect(screen.getByText("✎ edited")).toBeInTheDocument();
    expect(fake.callsTo("POST", "/api/cases/:id/treatment-edits")[0].body).toEqual({
      nodeId: "IBD-N51",
      newValues: { frequency: "three times daily" },
    });
  });

  it("chooses a grey option from the panel and lights its tier", async () => {
    const optionMap: MapNode[] = [
      {
        nodeId: "IBD-N41",
        type: "treatment_tier",
        label: "UC Tier 2",
        column: "treatment",
        status: "entry",
        result: null,
      },
      {
        nodeId: "IBD-N51",
        type: "drug",
        label: "Hydrocortisone 100 mg IV",
        column: "treatment",
        status: "option",
        result: null,
      },
      {
        nodeId: "IBD-N52",
        type: "drug",
        label: "Methylprednisolone 60 mg IV",
        column: "treatment",
        status: "option",
        result: null,
      },
    ];
    const fake = installFakeApi();
    fake.walkStreams.push([
      { type: "map_update", payload: { walkId: "wk-1", nodes: optionMap, edges: [] } },
      ...ANSWER_EVENTS.slice(-1),
    ]);
    fake.on("POST /api/cases/:id/traverse", () => ({
      map: {
        version: "IBD 1.0",
        nodes: optionMap.map((n) => (n.nodeId === "IBD-N51" ? { ...n, status: "chosen" } : n)),
        edges: [],
        selectedPath: ["IBD-N41", "IBD-N51"],
      },
      notice: "Hydrocortisone 100 mg IV chosen. Its tier's monitoring is now highlighted.",
      path: {
        drug: { nodeId: "IBD-N51", label: "Hydrocortisone 100 mg IV", type: "drug" },
        tier: { nodeId: "IBD-N41", label: "UC Tier 2", type: "treatment_tier" },
        review: [],
        monitor: [],
        watchOuts: [],
        nextTiers: [],
      },
    }));
    renderApp("/cases/BR-000001");
    await userEvent.type(await screen.findByLabelText(/Describe the patient/), "case");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByTestId("walk-summary");
    const drug = document.querySelector<HTMLElement>('[data-map-node="IBD-N51"]')!;
    expect(drug).toHaveTextContent("○ Option");
    await userEvent.click(drug);
    await userEvent.click(await screen.findByRole("button", { name: "Choose this option" }));
    expect(fake.callsTo("POST", "/api/cases/:id/traverse")[0].body).toEqual({
      nodeId: "IBD-N51",
    });
    await waitFor(() =>
      expect(document.querySelector('[data-map-node="IBD-N51"]')).toHaveTextContent("✓ Chosen"),
    );
    expect(await screen.findByText(/Hydrocortisone 100 mg IV chosen/)).toBeInTheDocument();
    expect(screen.getByTestId("path-card")).toHaveTextContent("Now on Hydrocortisone 100 mg IV");
  });

  it("shows the synthetic patient card with the allergy and saves new details", async () => {
    const fake = installFakeApi({
      "PATCH /api/cases/:id/patient": () =>
        caseView({ patient: { ...caseView().patient, weightKg: 60 } }),
    });
    renderApp("/cases/BR-000001");
    expect(await screen.findByText("Demo Patient A")).toBeInTheDocument();
    expect(screen.getByTestId("case-id")).toHaveTextContent("BR-000001 · synthetic");
    expect(screen.getByText(/Allergy: penicillin/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Expand ▾" }));
    expect(screen.getByRole("button", { name: "Collapse ▴" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    await userEvent.click(screen.getByRole("button", { name: "Edit details" }));
    const weight = screen.getByLabelText("Weight (kg)");
    await userEvent.clear(weight);
    await userEvent.type(weight, "60");
    await userEvent.click(screen.getByRole("button", { name: "Save details" }));
    expect(await screen.findByText(/58|60 kg/)).toHaveTextContent("60 kg");
    expect(fake.callsTo("PATCH", "/api/cases/:id/patient")[0].body).toEqual({
      sex: "female",
      weightKg: 60,
      allergies: ["penicillin"],
      comorbidities: [],
    });
    expect(screen.getByText("Patient details updated. Doses are re-read.")).toBeInTheDocument();
  });
});
