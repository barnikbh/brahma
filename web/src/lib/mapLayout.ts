// A free (non-columnar) map layout. Nodes start in layers by how far they are from the
// start of the care path, then a few rounds of spring and push forces relax them into an
// organic shape. Deterministic: the same nodes and edges always land in the same place.
// Pack-authored positions (`pos`) are kept exactly.

import type { MapEdge, MapNode } from "@/api/types";

export const NODE_W = 190;
export const NODE_H = 92;
const GAP_X = 70;
const GAP_Y = 28;

export interface Point {
  x: number;
  y: number;
}

/** Layer of each node: its longest distance from a node with no incoming edge. */
export function layers(nodes: MapNode[], edges: MapEdge[]): Map<string, number> {
  const known = new Set(nodes.map((n) => n.nodeId));
  const depth = new Map<string, number>(nodes.map((n) => [n.nodeId, 0]));
  const usable = edges.filter((e) => known.has(e.from) && known.has(e.to) && e.from !== e.to);
  for (let round = 0; round < nodes.length; round++) {
    let changed = false;
    for (const e of usable) {
      const next = (depth.get(e.from) ?? 0) + 1;
      if (next > (depth.get(e.to) ?? 0) && next <= nodes.length) {
        depth.set(e.to, next);
        changed = true;
      }
    }
    if (!changed) break;
  }
  return depth;
}

/**
 * Layered layout that never overlaps. Nodes sit in layers by distance from the start of
 * the care path; inside a layer they are ordered by the average height of their parents
 * (so edges stay short). A layer is one stack centred on the same line, never wrapped:
 * a wrapped stack makes an edge run through another node and look attached to it.
 * Pack-set positions are kept.
 */
export function freeLayout(nodes: MapNode[], edges: MapEdge[]): Map<string, Point> {
  const depth = layers(nodes, edges);
  const byLayer = new Map<number, MapNode[]>();
  const sorted = [...nodes].sort((a, b) =>
    a.nodeId.localeCompare(b.nodeId, undefined, { numeric: true }),
  );
  for (const node of sorted) {
    const layer = depth.get(node.nodeId) ?? 0;
    byLayer.set(layer, [...(byLayer.get(layer) ?? []), node]);
  }
  const parents = new Map<string, string[]>();
  for (const e of edges) parents.set(e.to, [...(parents.get(e.to) ?? []), e.from]);
  const out = new Map<string, Point>();
  const rowOf = new Map<string, number>();
  let column = 0;
  for (const layer of [...byLayer.keys()].sort((a, b) => a - b)) {
    const members = byLayer.get(layer) ?? [];
    const score = (n: MapNode): number => {
      const ps = (parents.get(n.nodeId) ?? []).filter((id) => rowOf.has(id));
      return ps.length ? ps.reduce((sum, id) => sum + (rowOf.get(id) ?? 0), 0) / ps.length : 0;
    };
    const ordered = [...members].sort((a, b) => score(a) - score(b));
    const top = -((ordered.length - 1) * (NODE_H + GAP_Y)) / 2;
    ordered.forEach((node, i) => {
      const y = top + i * (NODE_H + GAP_Y);
      out.set(node.nodeId, { x: column * (NODE_W + GAP_X), y });
      rowOf.set(node.nodeId, y);
    });
    column += 1;
  }
  for (const node of nodes) {
    if (node.pos) out.set(node.nodeId, { x: node.pos[0], y: node.pos[1] });
  }
  let minX = Infinity;
  let minY = Infinity;
  for (const p of out.values()) {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
  }
  for (const p of out.values()) {
    p.x = Math.round(p.x - minX + 8);
    p.y = Math.round(p.y - minY + 8);
  }
  return out;
}

/** Statuses that mean the care path is here now: the focus view centres on them. */
const CURRENT = new Set([
  "entry",
  "chosen",
  "now",
  "todo_first",
  "due",
  "watch",
  "present",
  "test_needed",
  "option",
  "tried",
]);

// What never happened: alternatives not taken and steps for later. Focus view hides these
// unless they sit right next to something current.
const NOT_HAPPENED = new Set(["not_taken", "planned", "bypassed", "not_in_pack"]);

/** The nodes to show in focus view: the patient's whole journey so far (findings, state,
 *  results, steps done or tried) and everything current, plus the not-yet-happened nodes
 *  directly linked to a current one, and the selected node. */
export function focusIds(nodes: MapNode[], edges: MapEdge[], selected: string | null): Set<string> {
  const current = new Set(nodes.filter((n) => CURRENT.has(n.status)).map((n) => n.nodeId));
  const keep = new Set(nodes.filter((n) => !NOT_HAPPENED.has(n.status)).map((n) => n.nodeId));
  for (const e of edges) {
    if (current.has(e.from)) keep.add(e.to);
    if (current.has(e.to)) keep.add(e.from);
  }
  if (selected) keep.add(selected);
  return keep;
}
