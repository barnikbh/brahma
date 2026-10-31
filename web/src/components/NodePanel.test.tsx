import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { apiError, installFakeApi, nodeDetail } from "@/test/fakeApi";
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
});
