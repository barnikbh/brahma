// The graph region used, on React Flow with fixed columns (BR3.5, interaction-spec
// NetworkMap). Positions are computed once per map; light-up only changes classes.

import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { memo, useMemo, type CSSProperties, type KeyboardEvent } from "react";
import type { MapEdge, MapNode, MapStatus, TherapyResponse } from "@/api/types";
import { ResultBadge, resultKind } from "@/components/ResultBadge";
import { cn } from "@/lib/utils";

export const COLUMNS = ["findings", "diagnosis", "tests", "subtype", "treatment", "monitor"];
const COLUMN_TITLES: Record<string, string> = {
  findings: "Findings",
  diagnosis: "Diagnosis",
  tests: "Tests",
  subtype: "Sub-type",
  treatment: "Treatment",
  monitor: "Monitor · watch",
};
const NODE_W = 190;
const NODE_H = 92;
const COL_WIDTH = NODE_W + 70;
const ROW_HEIGHT = NODE_H + 24;
const TOP = 40;

export const STATUS_BADGE: Record<MapStatus, { symbol: string; word: string }> = {
  used: { symbol: "✓", word: "Matched" },
  entry: { symbol: "▶", word: "Start here" },
  test_needed: { symbol: "?", word: "Test needed" },
  not_in_pack: { symbol: "⊘", word: "Not in pack" },
  bypassed: { symbol: "–", word: "Bypassed" },
  not_taken: { symbol: "⋯", word: "Not taken" },
  exploring: { symbol: "⤳", word: "Exploring" },
  tried: { symbol: "↺", word: "Tried" },
  option: { symbol: "○", word: "Option" },
  planned: { symbol: "→", word: "Suggested" },
  chosen: { symbol: "✓", word: "Chosen" },
};

// How a prior therapy went, as the doctor gave it in the treatment history.
export const RESPONSE_WORDS: Record<TherapyResponse, string> = {
  failed: "failed",
  lost_response: "lost response",
  intolerant: "not tolerated",
  responded: "responded",
};

interface MapNodeData extends Record<string, unknown> {
  node: MapNode;
  order: number;
  selected: boolean;
  onSelect: (nodeId: string) => void;
  onKey: (event: KeyboardEvent<HTMLButtonElement>, nodeId: string) => void;
}

// Columns the walk recommends rather than confirms: a walked node there is a
// suggestion for the doctor to act on, never something already done.
const PLAN_COLUMNS = new Set(["treatment", "monitor"]);

/** The badge for a node: walked findings and tests are matched; plan steps are suggested. */
export function badgeFor(node: MapNode): { symbol: string; word: string } {
  if (node.status === "tried") {
    const response = node.result?.response;
    const word = response ? RESPONSE_WORDS[response] : null;
    return { symbol: "↺", word: word ? `Tried · ${word}` : "Tried" };
  }
  if (node.status === "used" && PLAN_COLUMNS.has(node.column)) {
    return { symbol: "→", word: "Suggested" };
  }
  if (node.status === "used" && node.column === "tests" && node.result?.value) {
    return { symbol: "✓", word: "Result in" };
  }
  return STATUS_BADGE[node.status];
}

function nodeLabel(node: MapNode): string {
  const badge = badgeFor(node);
  const result = node.result?.value ? `, result ${node.result.value}` : "";
  return `${node.type}, ${node.label}, ${badge.word}${result}`;
}

const GraphNode = memo(function GraphNode({ data }: NodeProps<Node<MapNodeData>>) {
  const { node, order, selected, onSelect, onKey } = data;
  const badge = badgeFor(node);
  return (
    <>
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <button
        type="button"
        data-map-node={node.nodeId}
        data-status={node.status}
        aria-label={nodeLabel(node)}
        aria-pressed={selected}
        onClick={() => onSelect(node.nodeId)}
        onKeyDown={(e) => onKey(e, node.nodeId)}
        style={{ width: NODE_W, height: NODE_H, animationDelay: `${Math.min(order * 60, 1500)}ms` }}
        className={cn(
          "nopan nodrag brahma-light-up flex flex-col items-stretch gap-1 overflow-hidden rounded-md border bg-white px-2.5 py-2 text-left text-xs leading-snug focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2",
          (node.status === "used" || node.status === "chosen") &&
            "border-2 border-brand-700 bg-brand-50",
          node.status === "entry" && "border-2 border-brand-900 bg-brand-50",
          node.status === "test_needed" && "border-dashed border-result-pending",
          node.status === "not_in_pack" && "border-dashed border-neutral-400 text-ink-quiet",
          (node.status === "bypassed" ||
            node.status === "not_taken" ||
            node.status === "option" ||
            node.status === "planned") &&
            "border-dashed border-neutral-400 text-ink-quiet",
          node.status === "exploring" && "border-2 border-dashed border-explore bg-fuchsia-50",
          node.status === "tried" && "border-dashed border-neutral-500 bg-neutral-50",
          selected && "ring-4 ring-brand-200",
        )}
      >
        <span className="flex w-full items-baseline justify-between gap-2 font-mono text-[10px] uppercase text-ink-quiet">
          <span className="min-w-0 truncate">{node.type.replace(/_/g, " ")}</span>
          <span className="shrink-0">{node.nodeId}</span>
        </span>
        <span className="line-clamp-2 font-semibold" title={node.label}>
          {node.label}
        </span>
        <span className="mt-auto flex w-full min-w-0 items-center gap-2 text-[11px]">
          <span className="shrink-0">
            <span aria-hidden="true">{badge.symbol} </span>
            {badge.word}
          </span>
          {node.result?.value ? (
            <span className="min-w-0 truncate" title={node.result.value}>
              <ResultBadge kind={resultKind(node.result.value)} value={node.result.value} compact />
            </span>
          ) : null}
        </span>
      </button>
      <Handle type="source" position={Position.Right} className="!opacity-0" />
    </>
  );
});

function ColumnTitle({ data }: NodeProps<Node<{ title: string }>>) {
  return (
    <span className="block text-xs font-semibold uppercase tracking-wide text-ink-quiet">
      {data.title}
    </span>
  );
}

const nodeTypes = { brahma: GraphNode, column: ColumnTitle };

function ignoreNodeClick(): void {}

const EDGE_STYLE: Record<MapEdge["style"], CSSProperties> = {
  walked: { stroke: "#4338CA", strokeWidth: 2 },
  bypassed: { stroke: "#a3a3a3", strokeWidth: 1.5 },
  not_taken: { stroke: "#a3a3a3", strokeWidth: 1.5, strokeDasharray: "3 4" },
  exploring: { stroke: "#A21CAF", strokeWidth: 2, strokeDasharray: "6 4" },
};

/**
 * Fixed-column layout: column from the node, row by order within its column.
 * Shorter columns are centred against the tallest one, so edges stay short.
 */
export function layout(nodes: MapNode[]): Map<string, { x: number; y: number }> {
  const counts = new Map<string, number>();
  for (const node of nodes) counts.set(node.column, (counts.get(node.column) ?? 0) + 1);
  const tallest = Math.max(0, ...counts.values());
  const rows = new Map<string, number>();
  const out = new Map<string, { x: number; y: number }>();
  for (const node of nodes) {
    const col = Math.max(0, COLUMNS.indexOf(node.column));
    const row = rows.get(node.column) ?? 0;
    rows.set(node.column, row + 1);
    const offset = ((tallest - (counts.get(node.column) ?? 0)) * ROW_HEIGHT) / 2;
    out.set(node.nodeId, { x: col * COL_WIDTH + 8, y: TOP + offset + row * ROW_HEIGHT });
  }
  return out;
}

export interface GraphCanvasProps {
  nodes: MapNode[];
  edges: MapEdge[];
  version: string;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  /** Walk order for arrow-key moves; defaults to the node order. */
  order?: string[];
  readOnly?: boolean;
  title?: string;
}

export function GraphCanvas(props: GraphCanvasProps) {
  const { nodes, edges, selectedNodeId, onSelectNode } = props;
  const positions = useMemo(() => layout(nodes), [nodes]);
  const order = useMemo(() => {
    const known = new Set(nodes.map((n) => n.nodeId));
    const walk = (props.order ?? []).filter((id) => known.has(id));
    return [...walk, ...nodes.map((n) => n.nodeId).filter((id) => !walk.includes(id))];
  }, [nodes, props.order]);

  const onKey = (event: KeyboardEvent<HTMLButtonElement>, nodeId: string) => {
    const index = order.indexOf(nodeId);
    let next: string | undefined;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = order[index + 1];
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = order[index - 1];
    if (!next) return;
    event.preventDefault();
    const target = document.querySelector<HTMLButtonElement>(`[data-map-node="${next}"]`);
    target?.focus();
  };

  const titles: Node[] =
    nodes.length === 0
      ? []
      : COLUMNS.map((column, i) => ({
          id: `column-${column}`,
          type: "column",
          position: { x: i * COL_WIDTH + 8, y: 0 },
          width: NODE_W,
          height: 20,
          data: { title: COLUMN_TITLES[column] },
          draggable: false,
          selectable: false,
          focusable: false,
        }));
  const mapNodes: Node<MapNodeData>[] = nodes.map((node, i) => ({
    id: node.nodeId,
    type: "brahma",
    position: positions.get(node.nodeId) ?? { x: 0, y: 0 },
    width: NODE_W,
    height: NODE_H,
    data: {
      node,
      order: Math.max(0, order.indexOf(node.nodeId)) || i,
      selected: node.nodeId === selectedNodeId,
      onSelect: onSelectNode,
      onKey,
    },
    draggable: false,
    selectable: false,
    focusable: false,
  }));
  const flowNodes: Node[] = [...titles, ...mapNodes];
  const flowEdges: Edge[] = edges.map((edge) => ({
    id: edge.edgeId,
    source: edge.from,
    target: edge.to,
    type: "smoothstep",
    style: EDGE_STYLE[edge.style],
    animated: edge.style === "exploring",
    focusable: false,
    selectable: false,
  }));

  return (
    <section
      aria-label={props.title ?? "Graph region used"}
      className="rounded-card border border-neutral-300 bg-white p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">
          {props.title ?? "Graph region used"}
          {props.version ? (
            <span className="ml-2 font-mono text-xs font-normal text-ink-quiet">
              {props.version} · network map{props.readOnly ? " · read-only replay" : ""}
            </span>
          ) : null}
        </h2>
        <ul className="flex flex-wrap gap-3 text-[11px] text-ink-quiet" aria-label="Legend">
          <li>
            <span className="text-brand-700">━</span> Path walked
          </li>
          <li>─ Bypassed</li>
          <li>┄ Not taken</li>
          <li>
            <span className="text-explore">╌</span> Exploring
          </li>
          <li>
            ✓ Matched · → Suggested · ▶ Start here · ↺ Tried · ○ Option · ✓ Chosen · ? Test needed ·
            ⊘ Not in pack
          </li>
        </ul>
      </div>
      <div
        role="application"
        aria-label="Graph region used: use arrow keys to move between nodes, Enter to open one"
        className="relative h-[calc(100vh-260px)] min-h-[520px] w-full overflow-hidden rounded border border-neutral-200"
      >
        {nodes.length === 0 ? (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-ink-quiet">
            The map fills in as Brahma walks
          </p>
        ) : null}
        <ReactFlow
          key={`${props.version}-${nodes.length}`}
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.08 }}
          minZoom={0.2}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          nodesFocusable={false}
          // A click handler keeps pointer events on the (non-selectable) nodes, so the
          // node buttons receive real clicks; the buttons do the selecting.
          onNodeClick={ignoreNodeClick}
          edgesFocusable={false}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={24} color="#e5e5e5" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </section>
  );
}
