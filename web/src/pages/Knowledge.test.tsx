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
import type { Proposal } from "@/api/types";
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
    expect(screen.getByRole("button", { name: "Approve and publish 1.1" })).toBeDisabled();
  });

  it("lets the reviewer publish a clean proposal and shows before and after", async () => {
    const fake = installFakeApi({
      "GET /api/session": () => sessionView(REVIEWER),
      "POST /api/knowledge/proposals/:id/publish": () =>
        proposal({ status: "published", publishedVersion: "1.1" }),
    });
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Clarify the review day/ }));
    expect(screen.getByLabelText("Summary before")).toHaveTextContent("Old paraphrase.");
    expect(screen.getByLabelText("Summary after")).toHaveTextContent("New paraphrase.");
    expect(screen.getByText("Old")).toContainHTML("<del");
    expect(screen.getByText(/A synthetic source passage./)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve and publish 1.1" }));
    expect(fake.callsTo("POST", "/api/knowledge/proposals/:id/publish")).toHaveLength(1);
  });

  it("shows a doctor no Publish or Reject", async () => {
    installFakeApi();
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Clarify the review day/ }));
    expect(screen.getByRole("article", { name: "Proposal review" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Approve/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Waiting for a clinical reviewer/)).toBeInTheDocument();
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
      await screen.findByLabelText("What should change?"),
      "Update ustekinumab maintenance dose",
    );
    await userEvent.click(screen.getByRole("button", { name: "Read source and draft" }));
    expect(await screen.findByText("Which source URL supports the change?")).toBeInTheDocument();
    expect(screen.getByLabelText("What should change?")).toHaveValue("");
    await userEvent.type(screen.getByLabelText("Source website"), "example.org/page");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText(/I drafted changes to 1 node/)).toBeInTheDocument();
    expect(fake.callsTo("POST", "/api/knowledge/updates")[1].body).toEqual({
      text: "Update the graph from this source.\n\nSource: https://example.org/page",
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
    await userEvent.type(screen.getByLabelText("What should change?"), "Try again later");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(
      await screen.findByText(/the model call failed Your message is kept./),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("What should change?")).toHaveValue("Try again later");
    await userEvent.click(screen.getByRole("button", { name: "Start over" }));
    expect(screen.queryByText("Earlier question")).not.toBeInTheDocument();
  });

  it("carries a browsed node into the update box", async () => {
    installFakeApi();
    renderApp("/knowledge?node=IBD-N54");
    await userEvent.click(await screen.findByRole("button", { name: "Update this node" }));
    expect(await screen.findByLabelText("What should change?")).toHaveValue(
      "Update Ustekinumab 90 mg SC (IBD-N54)",
    );
  });

  it("starts afresh after a finished update instead of restoring it", async () => {
    installFakeApi({
      "GET /api/knowledge/updates": () => ({
        threads: [thread({ status: "stuck", messages: [msg(0, "assistant", "I could not.")] })],
      }),
    });
    renderApp("/knowledge");
    const box = await screen.findByLabelText("What should change?");
    expect(box).toBeEnabled();
    expect(screen.queryByText("I could not.")).not.toBeInTheDocument();
  });

  it("keeps going after an update stops, in a new conversation", async () => {
    const stuck = thread({
      status: "stuck",
      messages: [msg(0, "doctor", "Update it"), msg(1, "assistant", "I could not.")],
    });
    const fake = installFakeApi({ "POST /api/knowledge/updates": () => stuck });
    renderApp("/knowledge");
    await userEvent.type(await screen.findByLabelText("What should change?"), "Update it");
    await userEvent.click(screen.getByRole("button", { name: "Read source and draft" }));
    expect(await screen.findByText(/stopped without a draft/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("What should change?"), "Again");
    await userEvent.click(screen.getByRole("button", { name: "Read source and draft" }));
    await screen.findByText("I could not.");
    const sent = fake.callsTo("POST", "/api/knowledge/updates")[1].body as { threadId?: string };
    expect(sent.threadId).toBeUndefined();
  });

  it("drafts from a source URL and shows the new node with its source, then opens it", async () => {
    const drafted = bandProposal();
    let current = drafted;
    const done = thread({
      status: "proposed",
      messages: [
        msg(0, "doctor", "Update the graph from this source."),
        msg(1, "assistant", "I drafted changes to 1 node(s): IBD-N104 (new).", drafted.proposalId),
      ],
      proposals: [drafted],
    });
    const fake = installFakeApi({
      "GET /api/session": () => sessionView(REVIEWER),
      "GET /api/knowledge/proposals": () => ({ proposals: [current] }),
      "POST /api/knowledge/updates": () => done,
      "POST /api/knowledge/proposals/:id/publish": () => {
        current = bandProposal({ status: "published", publishedVersion: "1.2" });
        return current;
      },
    });
    renderApp("/knowledge");
    await userEvent.type(
      await screen.findByLabelText("Source website"),
      "https://example.org/dosing",
    );
    await userEvent.click(screen.getByRole("button", { name: "Read source and draft" }));
    const card = await screen.findByTestId("node-change-IBD-N104");
    expect(within(card).getByText("New node")).toBeInTheDocument();
    expect(within(card).getByTestId("dose-bands")).toHaveTextContent(
      "≤55 kg: 260 mg>55 to 85 kg: 390 mg>85 kg: 520 mg",
    );
    const source = within(card).getByRole("region", { name: "Source" });
    expect(within(source).getByRole("link", { name: "Synthetic dosing note" })).toHaveAttribute(
      "href",
      "https://example.org/dosing",
    );
    expect(source).toHaveTextContent("IBD-S21 · Dosing");
    expect(card).toHaveTextContent("Offered from");
    await userEvent.click(screen.getByRole("button", { name: "Approve and publish 1.2" }));
    expect(fake.callsTo("POST", "/api/knowledge/proposals/:id/publish")).toHaveLength(1);
    // The card stays on screen through the session refresh, now showing where it went.
    expect(await screen.findByText(/Live in IBD 1.2/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Open node" })).toBeInTheDocument();
  });

  it("shows only the changed values of an updated node, and the dose as bands", async () => {
    installFakeApi({
      "GET /api/knowledge/proposals": () => ({
        proposals: [
          proposal({
            comment: "Reword",
            changes: [
              {
                nodeId: "IBD-N54",
                before: {
                  label: "Same",
                  content: "Same",
                  fields: { route: "oral", doseValue: 5, doseUnit: "mg/kg", doseBasis: "per_kg" },
                },
                after: {
                  label: "Same",
                  content: "Same",
                  fields: {
                    route: "oral",
                    doseValue: 260,
                    doseUnit: "mg",
                    doseBasis: "weight_band",
                    doseBands: BANDS,
                  },
                },
                sourcePassage: null,
                copyFlag: false,
              },
            ],
          }),
        ],
      }),
    });
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Reword/ }));
    expect(screen.getByLabelText("Dose before")).toHaveTextContent("5 mg/kg per kg");
    expect(screen.getByLabelText("Dose after")).toHaveTextContent("≤55 kg: 260 mg");
    expect(screen.queryByLabelText("Route before")).not.toBeInTheDocument();
    expect(screen.getByText("Updated")).toBeInTheDocument();
  });

  it("opens a published node in Browse", async () => {
    const published = bandProposal({ status: "published", publishedVersion: "1.2" });
    installFakeApi({ "GET /api/knowledge/proposals": () => ({ proposals: [published] }) });
    renderApp("/knowledge");
    await userEvent.click(await screen.findByRole("button", { name: /Add induction/ }));
    expect(screen.getByText(/Live in IBD 1.2/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open node" }));
    const detail = await screen.findByRole("article", { name: "Node detail" });
    expect((await within(detail).findAllByText("IBD-N104")).length).toBeGreaterThan(0);
  });
});

const BANDS = [
  { weightMinKg: null, weightMaxKg: 55, doseValue: 260, doseUnit: "mg" },
  { weightMinKg: 55, weightMaxKg: 85, doseValue: 390, doseUnit: "mg" },
  { weightMinKg: 85, weightMaxKg: null, doseValue: 520, doseUnit: "mg" },
];

function bandProposal(overrides: Partial<Proposal> = {}): Proposal {
  return proposal({
    proposalId: "pr-9",
    baseVersion: "1.1",
    targetVersion: "1.2 draft",
    origin: "drafted",
    comment: "Add induction",
    changes: [
      {
        nodeId: "IBD-N104",
        before: null,
        after: {
          label: "Ustekinumab IV induction",
          content: "One infusion by body weight.",
          fields: { route: "intravenous", doseBasis: "weight_band", doseBands: BANDS },
        },
        sourcePassage: "A synthetic passage.",
        sourceUrl: "https://example.org/dosing",
        copyFlag: false,
      },
    ],
    changeSet: { addEdges: [{ fromNodeId: "IBD-N42", toNodeId: "IBD-N104" }] },
    citedSources: [
      {
        sourceId: "IBD-S21",
        title: "Synthetic dosing note",
        year: 2026,
        section: "Dosing",
        url: "https://example.org/dosing",
      },
    ],
    ...overrides,
  });
}

function msg(
  position: number,
  role: "doctor" | "assistant",
  text: string,
  proposalId: string | null = null,
) {
  return { position, role, text, proposalId, createdAt: "2026-10-30T10:00:00Z" };
}
