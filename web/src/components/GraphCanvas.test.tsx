import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { MapNode } from "@/api/types";
import { DEMO_NODES, FOLLOW_UP_NODES } from "@/test/fakeApi";
import { GraphCanvas, badgeFor, layout } from "./GraphCanvas";
import { ResultBadge, resultKind } from "./ResultBadge";

const node = (id: string) => document.querySelector<HTMLElement>(`[data-map-node="${id}"]`)!;

describe("GraphCanvas", () => {
  it("marks prior therapies as tried with how they went, and the new tier as start here", () => {
    render(
      <GraphCanvas
        nodes={FOLLOW_UP_NODES}
        edges={[]}
        version="IBD 1.1"
        selectedNodeId={null}
        onSelectNode={() => undefined}
      />,
    );
    expect(node("IBD-N53")).toHaveTextContent("↺ Tried · failed");
    expect(node("IBD-N46")).toHaveTextContent("▶ Start here");
    expect(node("IBD-N54")).toHaveTextContent("→ Suggested");
    expect(screen.getByLabelText("Legend")).toHaveTextContent("↺ Tried");
    const bare = { ...FOLLOW_UP_NODES[0], status: "tried" as const, result: null };
    expect(badgeFor(bare).word).toBe("Tried");
  });

  it("lays nodes out in fixed columns, in order within a column", () => {
    const positions = layout(DEMO_NODES);
    expect(positions.get("IBD-N1")!.x).toBe(8);
    expect(positions.get("IBD-N1")!.y).toBeGreaterThanOrEqual(40);
    expect(positions.get("IBD-N3")!.x).toBe(8);
    expect(positions.get("IBD-N3")!.y).toBeGreaterThan(positions.get("IBD-N1")!.y);
    expect(positions.get("IBD-N10")!.x).toBeGreaterThan(8);
    expect(positions.get("IBD-N51")!.x).toBe(positions.get("IBD-N50")!.x);
  });

  it("labels every node with type, label, status and result, with symbols for badges", () => {
    render(
      <GraphCanvas
        nodes={DEMO_NODES}
        edges={[]}
        version="IBD 1.0"
        selectedNodeId="IBD-N51"
        onSelectNode={() => undefined}
      />,
    );
    expect(node("IBD-N20")).toHaveAttribute(
      "aria-label",
      "test, Stool culture, Result in, result negative",
    );
    expect(node("IBD-N50")).toHaveTextContent("▶ Start here");
    expect(node("IBD-N51")).toHaveTextContent("→ Suggested");
    expect(node("IBD-N51")).not.toHaveTextContent("Done");
    expect(node("IBD-N12")).toHaveTextContent("Not taken");
    expect(node("IBD-N51")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/IBD 1.0 · network map/)).toBeInTheDocument();
  });

  it("selects by click and moves between nodes with the arrow keys", async () => {
    const onSelect = vi.fn();
    render(
      <GraphCanvas
        nodes={DEMO_NODES}
        edges={[{ edgeId: "e1", from: "IBD-N1", to: "IBD-N10", style: "walked" }]}
        version="IBD 1.0"
        selectedNodeId={null}
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

  it("renders options and planned steps grey and the chosen drug blue", () => {
    const nodes: MapNode[] = [
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
        label: "Hydrocortisone",
        column: "treatment",
        status: "option",
        result: null,
      },
      {
        nodeId: "IBD-N70",
        type: "monitoring",
        label: "Stool frequency",
        column: "monitor",
        status: "planned",
        result: null,
      },
      {
        nodeId: "IBD-N52",
        type: "drug",
        label: "Methylprednisolone",
        column: "treatment",
        status: "chosen",
        result: null,
      },
    ];
    render(
      <GraphCanvas
        nodes={nodes}
        edges={[]}
        version="IBD 1.1"
        selectedNodeId={null}
        onSelectNode={() => undefined}
      />,
    );
    expect(node("IBD-N51")).toHaveTextContent("○ Option");
    expect(node("IBD-N51")).toHaveClass("border-dashed");
    expect(node("IBD-N70")).toHaveTextContent("→ Suggested");
    expect(node("IBD-N70")).toHaveClass("border-dashed");
    expect(node("IBD-N52")).toHaveTextContent("✓ Chosen");
    expect(node("IBD-N52")).toHaveClass("border-brand-700");
    expect(screen.getByLabelText("Legend")).toHaveTextContent("○ Option");
    expect(node("IBD-N51")).toHaveAttribute("aria-label", "drug, Hydrocortisone, Option");
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
