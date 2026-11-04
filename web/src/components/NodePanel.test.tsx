import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { apiError, installFakeApi, json, nodeDetail } from "@/test/fakeApi";
import { NodePanel } from "./NodePanel";

describe("NodePanel", () => {
  it("shows the dose with its formula and both safety states", async () => {
    const fake = installFakeApi();
    render(<NodePanel nodeId="IBD-N51" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Hydrocortisone 100 mg IV" })).toHaveFocus();
    expect(screen.getByTestId("dose")).toHaveTextContent("100 mg100 mg (fixed dose)");
    const conflict = document.querySelector('[data-safety="conflict"]')!;
    expect(conflict).toHaveTextContent("! Allergy conflict: penicillin class");
    expect(conflict).toHaveTextContent("IBD-N101");
    expect(document.querySelector('[data-safety="not_checked"]')).toHaveTextContent(
      "? Interactions: Not checked: no grounded safety data",
    );
    expect(screen.getByText("Suggested by pack IBD 1.0")).toBeInTheDocument();
    expect(fake.calls[0].url).toBe("/api/nodes/IBD%401.0/IBD-N51?caseId=BR-000001");
  });

  it("never shows 'no conflict' without a supporting node", async () => {
    installFakeApi({
      "GET /api/nodes/:v/:n": () =>
        nodeDetail({
          safety: [
            {
              check: "pregnancy",
              status: "ok",
              nodeIds: [],
              message: "No contraindication",
              drugNodeId: "IBD-N51",
            },
          ],
        }),
    });
    render(<NodePanel nodeId="IBD-N51" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />);
    await screen.findByTestId("dose");
    expect(screen.queryByText(/No contraindication/)).not.toBeInTheDocument();
    expect(document.querySelector('[data-safety="not_checked"]')).toHaveTextContent(
      "? Pregnancy: Not checked: no grounded safety data",
    );
  });

  it("focuses once on open and never yanks focus back when detail resolves late", async () => {
    let resolveDetail!: (response: Response) => void;
    const gate = new Promise<Response>((resolve) => {
      resolveDetail = resolve;
    });
    installFakeApi({ "GET /api/nodes/:v/:n": () => gate });
    render(
      <>
        <NodePanel nodeId="IBD-N51" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />
        <label>
          Elsewhere
          <input aria-label="elsewhere" />
        </label>
      </>,
    );
    expect(await screen.findByRole("heading", { name: "IBD-N51" })).toHaveFocus();
    const elsewhere = screen.getByLabelText("elsewhere");
    elsewhere.focus();
    resolveDetail(json(nodeDetail()));
    await screen.findByTestId("dose");
    expect(elsewhere).toHaveFocus();
  });

  it("shows Couldn't load this node with Retry, adds comments and closes on Escape", async () => {
    const fake = installFakeApi({
      "GET /api/nodes/:v/:n": () => apiError(404, "node_not_found", "No such node."),
    });
    const onClose = vi.fn();
    render(<NodePanel nodeId="IBD-N51" version="IBD 1.0" onClose={onClose} />);
    expect(await screen.findByText(/Couldn't load this node/)).toBeInTheDocument();
    fake.on("GET /api/nodes/:v/:n", () => nodeDetail());
    fake.on("POST /api/nodes/:v/:n/comments", () => ({
      commentId: "c-1",
      nodeId: "IBD-N51",
      authorProfileId: "p-maya",
      text: "Check the review day.",
      createdAt: "t",
    }));
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await userEvent.type(await screen.findByLabelText("Add a comment"), "Check the review day.");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(await screen.findByText("Check the review day.")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("offers Choose this option only when the node can be chosen", async () => {
    installFakeApi();
    const onChoose = vi.fn();
    const { rerender } = render(
      <NodePanel nodeId="IBD-N51" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />,
    );
    await screen.findByTestId("dose");
    expect(screen.queryByRole("button", { name: "Choose this option" })).not.toBeInTheDocument();
    rerender(
      <NodePanel
        nodeId="IBD-N51"
        version="IBD 1.0"
        caseId="BR-000001"
        onClose={vi.fn()}
        canChoose
        onChoose={onChoose}
      />,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Choose this option" }));
    expect(onChoose).toHaveBeenCalledTimes(1);
  });

  it("explains when choosing must wait and shows the path context", async () => {
    installFakeApi();
    render(
      <NodePanel
        nodeId="IBD-N51"
        version="IBD 1.0"
        caseId="BR-000001"
        onClose={vi.fn()}
        chooseUnavailable="Available once the walk answers."
        contextLine={{ prefix: "Option of", nodeId: "IBD-N41", label: "UC Tier 2" }}
      />,
    );
    await screen.findByTestId("dose");
    expect(screen.getByRole("button", { name: "Choose this option" })).toBeDisabled();
    expect(screen.getByText("Available once the walk answers.")).toBeInTheDocument();
    const context = screen.getByTestId("node-context");
    expect(context).toHaveTextContent("Option of");
    expect(context).toHaveTextContent("UC Tier 2");
    expect(context.querySelector('[data-node-chip="IBD-N41"]')).toBeInTheDocument();
  });

  it("shows where a met criterion leads, and nothing otherwise", async () => {
    const fake = installFakeApi();
    fake.on("GET /api/nodes/:v/:n", () =>
      nodeDetail({ leadsTo: [{ nodeId: "IBD-N42", label: "UC Tier 3" }] }),
    );
    const { unmount } = render(
      <NodePanel nodeId="IBD-N80" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />,
    );
    const leads = await screen.findByTestId("node-leads-to");
    expect(leads).toHaveTextContent("If met →");
    expect(leads).toHaveTextContent("UC Tier 3");
    expect(leads.querySelector('[data-node-chip="IBD-N42"]')).toBeInTheDocument();
    unmount();
    fake.on("GET /api/nodes/:v/:n", () => nodeDetail());
    render(<NodePanel nodeId="IBD-N51" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />);
    await screen.findByTestId("dose");
    expect(screen.queryByTestId("node-leads-to")).not.toBeInTheDocument();
  });

  it("records a day-3 result from a wired criterion", async () => {
    installFakeApi({
      "GET /api/nodes/:v/:n": () =>
        nodeDetail({
          node: {
            nodeId: "IBD-N81",
            type: "response_criterion",
            label: "Day 3 on IV steroids: CRP above 45 mg/L",
            content: "A CRP above 45 mg/L on day 3 means the patient is not responding.",
            fields: { measure: "CRP", threshold: 45, comparator: "gt", unit: "mg/L" },
            sourceIds: ["SRC-1"],
            column: "monitor",
          },
          leadsTo: [{ nodeId: "IBD-N42", label: "UC Tier 3" }],
        }),
    });
    const onReview = vi.fn();
    render(
      <NodePanel
        nodeId="IBD-N81"
        version="IBD 1.0"
        caseId="BR-000001"
        onClose={vi.fn()}
        onReview={onReview}
      />,
    );
    const form = await screen.findByTestId("node-review");
    expect(form).toHaveTextContent("Meets when CRP is above 45 mg/L");
    await userEvent.type(screen.getByLabelText("Day-3 result"), "60");
    await userEvent.click(screen.getByRole("button", { name: "Record" }));
    expect(onReview).toHaveBeenCalledWith("IBD-N81", "60");
  });

  it("shows no review form for unwired nodes or without a review handler", async () => {
    installFakeApi({
      "GET /api/nodes/:v/:n": () =>
        nodeDetail({
          node: {
            nodeId: "IBD-N81",
            type: "response_criterion",
            label: "Day 3 on IV steroids: CRP above 45 mg/L",
            content: "A CRP above 45 mg/L on day 3 means the patient is not responding.",
            fields: { measure: "CRP", threshold: 45, comparator: "gt", unit: "mg/L" },
            sourceIds: ["SRC-1"],
            column: "monitor",
          },
          leadsTo: [{ nodeId: "IBD-N42", label: "UC Tier 3" }],
        }),
    });
    const { unmount } = render(
      <NodePanel nodeId="IBD-N81" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />,
    );
    await screen.findByTestId("node-leads-to");
    expect(screen.queryByTestId("node-review")).not.toBeInTheDocument();
    unmount();
    render(
      <NodePanel
        nodeId="IBD-N81"
        version="IBD 1.0"
        caseId="BR-000001"
        onClose={vi.fn()}
        onReview={vi.fn()}
        readOnly
      />,
    );
    await screen.findByTestId("node-review");
    expect(screen.getByRole("button", { name: "Record" })).toBeDisabled();
  });

  it("navigates owner-authored next paths", async () => {
    installFakeApi({
      "GET /api/nodes/:v/:n": () =>
        nodeDetail({
          nextPaths: [{ nodeId: "IBD-N96", label: "Emergency colectomy triggers" }],
        }),
    });
    const onSelectNode = vi.fn();
    render(
      <NodePanel
        nodeId="IBD-N90"
        version="IBD 1.0"
        caseId="BR-000001"
        onClose={vi.fn()}
        onSelectNode={onSelectNode}
      />,
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Emergency colectomy triggers" }),
    );
    expect(onSelectNode).toHaveBeenCalledWith("IBD-N96");
  });

  it("shows the stored edit marker with no in-memory outcome (reload)", async () => {
    installFakeApi({
      "GET /api/nodes/:v/:n": () =>
        nodeDetail({
          edited: {
            editId: "te-1",
            caseId: "BR-000001",
            nodeId: "IBD-N51",
            original: { doseValue: 100 },
            newValues: { doseValue: 40 },
            editorProfileId: "p-maya",
            createdAt: "t",
          },
        }),
    });
    render(<NodePanel nodeId="IBD-N51" version="IBD 1.0" caseId="BR-000001" onClose={vi.fn()} />);
    expect(await screen.findByText("✎ edited")).toBeInTheDocument();
    expect(screen.getByText(/Edited by p-maya/)).toBeInTheDocument();
  });
});
