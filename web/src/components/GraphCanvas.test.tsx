import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { MapNode } from "@/api/types";
import { DEMO_NODES, FOLLOW_UP_NODES } from "@/test/fakeApi";
import { freeLayout } from "@/lib/mapLayout";
import { GraphCanvas, badgeFor } from "./GraphCanvas";
import { ResultBadge, resultKind } from "./ResultBadge";

const node = (id: string) => document.querySelector<HTMLElement>(`[data-map-node="${id}"]`)!;

describe("GraphCanvas", () => {
  it("marks prior therapies as tried with how they went, and the new tier as start here", () => {
    render(
      <GraphCanvas
        nodes={FOLLOW_UP_NODES}
        edges={[]}
        version="IBD 1.2"
        selectedNodeId={null}
        defaultFocus={false}
        onSelectNode={() => undefined}
      />,
    );
    expect(node("IBD-N53")).toHaveTextContent("↺ Tried · failed");
    expect(node("IBD-N46")).toHaveTextContent("▶ Now");
    expect(node("IBD-N54")).not.toHaveTextContent("Suggested");
    expect(screen.getByLabelText("Legend")).toHaveTextContent("Tried");
    const bare = { ...FOLLOW_UP_NODES[0], status: "tried" as const, result: null };
    expect(badgeFor(bare).word).toBe("Tried");
  });

  it("places nodes freely, without overlap, and keeps pack-set positions", () => {
    const nodes = DEMO_NODES.map((n) =>
      n.nodeId === "IBD-N1" ? { ...n, pos: [500, 300] as [number, number] } : n,
    );
    const edges = [{ edgeId: "e1", from: "IBD-N1", to: "IBD-N10", style: "walked" as const }];
    const positions = freeLayout(nodes, edges);
    expect(positions.size).toBe(nodes.length);
    const raw = freeLayout(DEMO_NODES, edges);
    expect(raw.get("IBD-N10")!.x).toBeGreaterThan(raw.get("IBD-N1")!.x);
    const spots = Array.from(positions.values()).map((p) => `${p.x},${p.y}`);
    expect(new Set(spots).size).toBe(spots.length);
  });

  it("labels every node with type, label, status and result, with symbols for badges", () => {
    render(
      <GraphCanvas
        nodes={DEMO_NODES}
        edges={[]}
        version="IBD 1.0"
        selectedNodeId="IBD-N51"
        defaultFocus={false}
        onSelectNode={() => undefined}
      />,
    );
    expect(node("IBD-N20")).toHaveAttribute(
      "aria-label",
      "test, Stool culture, Done, result negative",
    );
    expect(node("IBD-N50")).toHaveTextContent("▶ Now");
    expect(node("IBD-N51")).not.toHaveTextContent("Suggested");
    expect(node("IBD-N12")).toHaveTextContent("Not taken");
    expect(node("IBD-N51")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/IBD 1.0/)).toBeInTheDocument();
  });

  it("selects by click and moves between nodes with the arrow keys", async () => {
    const onSelect = vi.fn();
    render(
      <GraphCanvas
        nodes={DEMO_NODES}
        edges={[{ edgeId: "e1", from: "IBD-N1", to: "IBD-N10", style: "walked" }]}
        version="IBD 1.0"
        selectedNodeId={null}
        defaultFocus={false}
        onSelectNode={onSelect}
        order={["IBD-N1", "IBD-N10"]}
      />,
    );
    await userEvent.click(node("IBD-N10"));
    expect(onSelect).toHaveBeenCalledWith("IBD-N10");
    node("IBD-N1").focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(node("IBD-N10")).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(node("IBD-N1")).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenLastCalledWith("IBD-N1");
  });

  it("colours nodes by kind and never calls monitoring or watch-outs Suggested", () => {
    const base = { column: "monitor", result: null };
    const nodes: MapNode[] = [
      { ...base, nodeId: "A", type: "diagnosis", label: "UC", status: "used", kind: "state" },
      {
        ...base,
        nodeId: "B",
        type: "test",
        label: "TB screen",
        status: "todo_first",
        kind: "test",
      },
      { ...base, nodeId: "C", type: "drug", label: "Drug", status: "chosen", kind: "action" },
      {
        ...base,
        nodeId: "D",
        type: "monitoring",
        label: "CRP",
        status: "due",
        kind: "observation",
      },
      {
        ...base,
        nodeId: "E",
        type: "watch_out",
        label: "Megacolon",
        status: "watch",
        kind: "observation",
      },
      {
        ...base,
        nodeId: "F",
        type: "escalation",
        label: "Colectomy",
        status: "now",
        kind: "escalation",
      },
      {
        ...base,
        nodeId: "G",
        type: "monitoring",
        label: "Later",
        status: "planned",
        kind: "observation",
      },
    ];
    render(
      <GraphCanvas
        nodes={nodes}
        edges={[]}
        version="IBD 1.2"
        selectedNodeId={null}
        defaultFocus={false}
        onSelectNode={() => undefined}
      />,
    );
    expect(node("A")).toHaveAttribute("data-kind", "state");
    expect(node("A")).toHaveClass("bg-purple-50");
    expect(node("B")).toHaveClass("bg-blue-50");
    expect(node("B")).toHaveTextContent("To do first");
    expect(node("C")).toHaveClass("bg-teal-50");
    expect(node("C")).toHaveTextContent("Chosen");
    expect(node("D")).toHaveClass("bg-amber-50");
    expect(node("D")).toHaveTextContent("Due");
    expect(node("E")).toHaveTextContent("Watch for");
    expect(node("F")).toHaveTextContent("Now");
    expect(node("G")).toHaveTextContent("Later");
    expect(document.body).not.toHaveTextContent("Suggested");
    expect(screen.getByLabelText("Legend")).toHaveTextContent("To do first");
  });

  it("focus view keeps the patient's journey and hides only what never happened", () => {
    const base = { column: "tests", status: "used" as const };
    const nodes: MapNode[] = [
      { ...base, nodeId: "T", type: "test", label: "Colonoscopy", result: { value: "UC" } },
      { ...base, nodeId: "S", type: "subtype", label: "Severe UC", result: null },
      {
        ...base,
        nodeId: "P",
        type: "treatment_tier",
        label: "Old tier",
        status: "done",
        result: null,
      },
      { ...base, nodeId: "R", type: "drug", label: "Old drug", status: "tried", result: null },
      { ...base, nodeId: "F", type: "drug", label: "Far", status: "not_taken", result: null },
      { ...base, nodeId: "D", type: "drug", label: "Drug", status: "chosen", result: null },
    ];
    render(
      <GraphCanvas
        nodes={nodes}
        edges={[]}
        version="IBD 1.2"
        selectedNodeId={null}
        onSelectNode={() => undefined}
      />,
    );
    expect(node("T")).toHaveTextContent("Done");
    expect(node("S")).toHaveTextContent("Present");
    expect(node("P")).toHaveTextContent("Done");
    expect(node("R")).toHaveTextContent("Tried");
    expect(screen.getByTestId("timeline")).toHaveTextContent("Tried Old drug");
    expect(document.querySelector('[data-map-node="F"]')).toBeNull();
  });

  it("focus view hides what is not current until the whole map is asked for", async () => {
    const base = { column: "monitor", result: null, kind: "observation" as const };
    const nodes: MapNode[] = [
      { ...base, nodeId: "A", type: "symptom", label: "Far", status: "not_taken" },
      { ...base, nodeId: "B", type: "drug", label: "Here", status: "chosen" },
    ];
    render(
      <GraphCanvas
        nodes={nodes}
        edges={[]}
        version="IBD 1.2"
        selectedNodeId={null}
        onSelectNode={() => undefined}
        timeline={[{ nodeId: "A", label: "Far", kind: "present", at: "t" }]}
      />,
    );
    expect(document.querySelector('[data-map-node="A"]')).toBeNull();
    expect(node("B")).toBeInTheDocument();
    expect(screen.getByTestId("timeline")).toHaveTextContent("Far · present");
    await userEvent.click(screen.getByRole("button", { name: /show whole map/ }));
    expect(node("A")).toBeInTheDocument();
  });

  it("shows the empty hint before a walk", () => {
    render(
      <GraphCanvas nodes={[]} edges={[]} version="" selectedNodeId={null} onSelectNode={vi.fn()} />,
    );
    expect(screen.getByText("The map fills in as Brahma walks")).toBeInTheDocument();
  });
});

describe("ResultBadge", () => {
  it("shows a symbol and a word, not colour alone", () => {
    const { container } = render(
      <>
        <ResultBadge kind={resultKind("negative")} />
        <ResultBadge kind={resultKind("ulcerative colitis")} value="ulcerative colitis" />
        <ResultBadge kind={resultKind("")} />
        <ResultBadge kind={resultKind("low")} />
        <ResultBadge kind={resultKind("above range")} />
        <ResultBadge kind={resultKind("planned")} />
      </>,
    );
    const texts = Array.from(container.querySelectorAll("[data-result]")).map((b) => b.textContent);
    expect(texts).toEqual([
      "✓Normal",
      "!Abnormal· ulcerative colitis",
      "?Not yet tested",
      "↓Low",
      "↑High",
      "◷Planned",
    ]);
  });
});
