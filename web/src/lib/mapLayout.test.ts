import { describe, expect, it } from "vitest";
import type { MapEdge, MapNode } from "@/api/types";
import { NODE_H, NODE_W, freeLayout } from "./mapLayout";

const node = (id: string): MapNode => ({
  nodeId: id,
  type: "monitoring",
  label: id,
  column: "monitor",
  status: "planned",
  result: null,
});

describe("freeLayout", () => {
  it("never lets two nodes overlap, even with a crowd under one parent", () => {
    const nodes = ["T", ...Array.from({ length: 14 }, (_, i) => `M${i}`)].map(node);
    const edges: MapEdge[] = nodes
      .slice(1)
      .map((n) => ({ edgeId: `e-${n.nodeId}`, from: "T", to: n.nodeId, style: "walked" }));
    const spots = [...freeLayout(nodes, edges).values()];
    for (let i = 0; i < spots.length; i++) {
      for (let j = i + 1; j < spots.length; j++) {
        const apartX = Math.abs(spots[i]!.x - spots[j]!.x) >= NODE_W;
        const apartY = Math.abs(spots[i]!.y - spots[j]!.y) >= NODE_H;
        expect(apartX || apartY).toBe(true);
      }
    }
  });
});
