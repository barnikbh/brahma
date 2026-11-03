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
