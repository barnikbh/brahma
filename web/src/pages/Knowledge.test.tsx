import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import {
  BROWSE_GRAPH,
  REVIEWER,
  apiError,
  browseDetail,
  installFakeApi,
  proposal,
  sessionView,
  thread,
} from "@/test/fakeApi";
import { renderApp } from "@/test/render";

describe("KnowledgePage", () => {
  it("blocks Publish while the copy flag is set (reviewer)", async () => {
    installFakeApi({
      "GET /api/session": () => sessionView(REVIEWER),
      "GET /api/knowledge/proposals": () => ({
        proposals: [
          proposal({
            changes: [{ ...proposal().changes[0], copyFlag: true }],
            copyFlaggedNodeIds: ["IBD-N51"],
          }),
        ],
      }),
    });
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Clarify the review day/ }));
    expect(screen.getByTestId("copy-flag")).toHaveTextContent(
      "! Possible verbatim copy — publish blocked",
    );
    expect(screen.getByRole("button", { name: "Publish 1.1" })).toBeDisabled();
  });

  it("lets the reviewer publish a clean proposal and shows before and after", async () => {
    const fake = installFakeApi({
      "GET /api/session": () => sessionView(REVIEWER),
      "POST /api/knowledge/proposals/:id/publish": () =>
        proposal({ status: "published", publishedVersion: "1.1" }),
    });
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Clarify the review day/ }));
    expect(screen.getByText("Old paraphrase.")).toBeInTheDocument();
    expect(screen.getByText("New paraphrase.")).toBeInTheDocument();
    expect(screen.getByText(/A synthetic source passage./)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Publish 1.1" }));
    expect(fake.callsTo("POST", "/api/knowledge/proposals/:id/publish")).toHaveLength(1);
  });

  it("shows a doctor no Publish or Reject", async () => {
    installFakeApi();
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Clarify the review day/ }));
    expect(screen.getByRole("article", { name: "Proposal review" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Publish/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(screen.getByText("First version")).toBeInTheDocument();
  });

  it("walks the saved nodes: search, open, follow a connection, go back", async () => {
    installFakeApi();
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("tab", { name: "Browse nodes" }));
    expect(await screen.findByText("Bloody diarrhoea")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Search nodes"), "colitis");
    expect(screen.queryByText("Bloody diarrhoea")).not.toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Search nodes"));
    await userEvent.click(await screen.findByRole("button", { name: /Bloody diarrhoea/ }));
    const detail = await screen.findByRole("article", { name: "Node detail" });
    expect(await within(detail).findByText("Content of Bloody diarrhoea.")).toBeInTheDocument();
    expect(within(detail).getByTestId("updated-line")).toHaveTextContent("Initial pack v1.1");
    await userEvent.click(within(detail).getByRole("button", { name: "Ulcerative colitis" }));
    expect(await within(detail).findByText("Content of Ulcerative colitis.")).toBeInTheDocument();
    expect(
      within(within(detail).getByRole("navigation")).getByRole("button", {
        name: "Bloody diarrhoea",
      }),
    ).toBeInTheDocument();
    await userEvent.click(within(detail).getByRole("button", { name: "Ustekinumab 90 mg SC" }));
    expect(await within(detail).findByText("doseValue")).toBeInTheDocument();
    await userEvent.click(within(detail).getByRole("button", { name: "Back" }));
    expect(await within(detail).findByText("Content of Ulcerative colitis.")).toBeInTheDocument();
  });

  it("shows who last updated a node and when", async () => {
    const fake = installFakeApi();
    fake.on("GET /api/knowledge/nodes/:id", () =>
      browseDetail("IBD-N54", {
        updated: {
          nodeId: "IBD-N54",
          updatedBy: "p-maya",
          updatedByName: "Dr. Maya (demo)",
          approvedBy: "p-reviewer",
          approvedByName: "Demo reviewer",
          updatedAt: "2026-10-30T10:00:00Z",
          version: "1.2",
          proposalId: "pr-1",
        },
      }),
    );
    renderApp("/knowledge?node=IBD-N54");
    expect(await screen.findByTestId("updated-line")).toHaveTextContent(
      /Last updated by Dr\. Maya \(demo\) on .* \(IBD v1\.2\), approved by Demo reviewer/,
    );
  });

  it("shows a browse error and offers retry", async () => {
    const fake = installFakeApi({
      "GET /api/knowledge/graph": () => apiError(500, "boom", "Graph is down."),
    });
    renderApp("/knowledge?node=IBD-N1");
    expect(await screen.findByText("Graph is down.")).toBeInTheDocument();
    fake.on("GET /api/knowledge/graph", () => BROWSE_GRAPH);
    await userEvent.click(screen.getAllByRole("button", { name: "Retry" })[0]);
    expect((await screen.findAllByText("Bloody diarrhoea")).length).toBeGreaterThan(0);
  });

  it("answers a follow-up question, then shows the drafted proposal", async () => {
    const asked = thread({
      status: "open",
      rounds: 1,
      messages: [
        msg(0, "doctor", "Update ustekinumab maintenance dose"),
        msg(1, "assistant", "Which source URL supports the change?"),
      ],
    });
    const done = thread({
      status: "proposed",
      messages: [
        ...asked.messages,
        msg(2, "doctor", "Use https://example.org/page"),
        msg(3, "assistant", "I drafted changes to 1 node(s): IBD-N51.", "pr-9"),
      ],
      proposals: [proposal({ proposalId: "pr-9", comment: "Drafted comment" })],
    });
    const fake = installFakeApi({
      "GET /api/knowledge/proposals": () => ({ proposals: done.proposals }),
      "POST /api/knowledge/updates": (call) =>
        (call.body as { threadId?: string }).threadId ? done : asked,
    });
    renderApp("/knowledge");
    await userEvent.type(
      await screen.findByLabelText("Your message"),
      "Update ustekinumab maintenance dose",
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Which source URL supports the change?")).toBeInTheDocument();
    expect(screen.getByLabelText("Your message")).toHaveValue("");
    await userEvent.type(screen.getByLabelText("Your message"), "Use https://example.org/page");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(/I drafted changes to 1 node/)).toBeInTheDocument();
    expect(fake.callsTo("POST", "/api/knowledge/updates")[1].body).toEqual({
      text: "Use https://example.org/page",
      threadId: "th-1",
      pack: "IBD",
    });
    expect(await screen.findByRole("article", { name: "Proposal review" })).toBeInTheDocument();
  });

  it("keeps the message when sending fails and restores a saved conversation", async () => {
    installFakeApi({
      "GET /api/knowledge/updates": () => ({
        threads: [thread({ messages: [msg(0, "doctor", "Earlier question")] })],
      }),
      "POST /api/knowledge/updates": () =>
        apiError(502, "DraftFailed", "the draft could not be made: the model call failed"),
    });
    renderApp("/knowledge");
    expect(await screen.findByText("Earlier question")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Your message"), "Try again later");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(
      await screen.findByText(/the model call failed Your message is kept./),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Your message")).toHaveValue("Try again later");
    await userEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(screen.queryByText("Earlier question")).not.toBeInTheDocument();
  });

  it("carries a browsed node into the update box", async () => {
    installFakeApi();
    renderApp("/knowledge?node=IBD-N54");
    await userEvent.click(await screen.findByRole("button", { name: "Update this node" }));
    expect(await screen.findByLabelText("Your message")).toHaveValue(
      "Update Ustekinumab 90 mg SC (IBD-N54) from ",
    );
  });

  it("disables the box when the conversation has ended", async () => {
    installFakeApi({
      "GET /api/knowledge/updates": () => ({
        threads: [thread({ status: "stuck", messages: [msg(0, "assistant", "I could not.")] })],
      }),
    });
    renderApp("/knowledge");
    expect(await screen.findByText("I could not.")).toBeInTheDocument();
    expect(screen.getByText(/ended without a draft/)).toBeInTheDocument();
    expect(screen.getByLabelText("Your message")).toBeDisabled();
  });
});

function msg(
  position: number,
  role: "doctor" | "assistant",
  text: string,
  proposalId: string | null = null,
) {
  return { position, role, text, proposalId, createdAt: "2026-10-30T10:00:00Z" };
}
