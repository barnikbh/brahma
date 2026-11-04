// The care map on React Flow: nodes are colour-coded by kind and placed freely (pack-set
// positions, else an automatic relaxed layout). A focus view shows only what is current
// and its neighbours; a timeline strip lists what has happened in the case so far.

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
import {
  memo,
  useMemo,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import type {
  MapEdge,
  MapNode,
  MapStatus,
  NodeKind,
  TherapyResponse,
  TimelineItem,
} from "@/api/types";
import { ResultBadge, resultKind } from "@/components/ResultBadge";
import { cn } from "@/lib/utils";
import { NODE_H, NODE_W, focusIds, freeLayout } from "@/lib/mapLayout";

export const STATUS_BADGE: Record<MapStatus, { symbol: string; word: string }> = {
  used: { symbol: "●", word: "On path" },
  entry: { symbol: "▶", word: "Now" },
  now: { symbol: "▶", word: "Now" },
  todo_first: { symbol: "!", word: "To do first" },
  due: { symbol: "◔", word: "Due" },
  watch: { symbol: "◉", word: "Watch for" },
  present: { symbol: "●", word: "Present" },
  done: { symbol: "✓", word: "Done" },
  test_needed: { symbol: "◔", word: "Due" },
  not_in_pack: { symbol: "⊘", word: "Not in pack" },
  bypassed: { symbol: "–", word: "Bypassed" },
  not_taken: { symbol: "⋯", word: "Not taken" },
  exploring: { symbol: "⤳", word: "Exploring" },
  tried: { symbol: "↺", word: "Tried" },
  option: { symbol: "○", word: "Option" },
  planned: { symbol: "·", word: "Later" },
  chosen: { symbol: "✓", word: "Chosen" },
};

// How a prior therapy went, as the doctor gave it in the treatment history.
export const RESPONSE_WORDS: Record<TherapyResponse, string> = {
  failed: "failed",
  lost_response: "lost response",
  intolerant: "not tolerated",
  responded: "responded",
};

export const KIND_LABEL: Record<NodeKind, string> = {
  state: "Patient state",
  observation: "Observation",
  test: "Test",
  action: "Action",
  escalation: "Escalation",
};

// Kind colours: patient state purple, observation amber, test blue, action teal,
// escalation coral. Statuses change the border and badge, never the kind colour.
const KIND_CLASS: Record<NodeKind, string> = {
  state: "border-purple-500 bg-purple-50",
  observation: "border-amber-500 bg-amber-50",
  test: "border-blue-500 bg-blue-50",
  action: "border-teal-600 bg-teal-50",
  escalation: "border-[#e8604c] bg-[#fdeeea]",
};
const KIND_DOT: Record<NodeKind, string> = {
  state: "bg-purple-500",
  observation: "bg-amber-500",
  test: "bg-blue-500",
  action: "bg-teal-600",
  escalation: "bg-[#e8604c]",
};

const LIT = new Set<MapStatus>(["todo_first", "due", "watch", "present", "now", "test_needed"]);
const GREY = new Set<MapStatus>(["planned", "option", "not_taken", "bypassed", "not_in_pack"]);

interface MapNodeData extends Record<string, unknown> {
  node: MapNode;
  order: number;
  selected: boolean;
  onSelect: (nodeId: string) => void;
  onKey: (event: KeyboardEvent<HTMLButtonElement>, nodeId: string) => void;
}

const KIND_BY_TYPE: Record<string, NodeKind> = {
  diagnosis: "state",
  subtype: "state",
  test: "test",
  treatment_tier: "action",
  drug: "action",
  diet: "action",
  escalation: "escalation",
};

/** The node's kind from the server, else from its type (older maps carry no kind). */
export function kindOf(node: MapNode): NodeKind {
  return node.kind ?? KIND_BY_TYPE[node.type] ?? "observation";
}

/** The badge for a node. A walked test with a result is Done; a walked finding is Present. */
export function badgeFor(node: MapNode): { symbol: string; word: string } {
  if (node.status === "tried") {
    const response = node.result?.response;
    const word = response ? RESPONSE_WORDS[response] : null;
    return { symbol: "↺", word: word ? `Tried · ${word}` : "Tried" };
  }
  if (node.status === "used") {
    const kind = kindOf(node);
    if (kind === "test") return { symbol: "✓", word: "Done" };
    if (kind === "state" || node.column === "findings") return { symbol: "●", word: "Present" };
    if (kind === "action") return { symbol: "▶", word: "Now" }; // e.g. diet advice on the path
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
  const kind = kindOf(node);
  return (
    <>
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <button
        type="button"
        data-map-node={node.nodeId}
        data-status={node.status}
        data-kind={kind}
        aria-label={nodeLabel(node)}
        aria-pressed={selected}
        onClick={() => onSelect(node.nodeId)}
        onKeyDown={(e) => onKey(e, node.nodeId)}
        style={{ width: NODE_W, height: NODE_H, animationDelay: `${Math.min(order * 40, 1200)}ms` }}
        className={cn(
          "nopan nodrag brahma-light-up flex flex-col items-stretch gap-1 overflow-hidden rounded-md border-2 px-2.5 py-2 text-left text-xs leading-snug focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2",
          KIND_CLASS[kind],
          GREY.has(node.status) && "border-dashed opacity-70",
          node.status === "tried" && "border-dashed opacity-80",
          node.status === "exploring" && "border-dashed",
          LIT.has(node.status) && "ring-2 ring-offset-1 ring-neutral-800 shadow-md",
          (node.status === "chosen" || node.status === "entry") && "ring-2 ring-neutral-900",
          node.status === "done" && "opacity-90",
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
          <span className="shrink-0 font-medium">
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

const nodeTypes = { brahma: GraphNode };

function ignoreNodeClick(): void {}

const EDGE_STYLE: Record<MapEdge["style"], CSSProperties> = {
  walked: { stroke: "#4338CA", strokeWidth: 2 },
  bypassed: { stroke: "#a3a3a3", strokeWidth: 1.5 },
  not_taken: { stroke: "#a3a3a3", strokeWidth: 1.5, strokeDasharray: "3 4" },
  exploring: { stroke: "#A21CAF", strokeWidth: 2, strokeDasharray: "6 4" },
};

const EVENT_WORD: Record<TimelineItem["kind"], string> = {
  present: "present",
  result: "result",
  done: "done",
};

export interface GraphCanvasProps {
  nodes: MapNode[];
  edges: MapEdge[];
  version: string;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  /** Walk order for arrow-key moves; defaults to the node order. */
  order?: string[];
  timeline?: TimelineItem[];
  /** Start in focus view (default) or on the whole map. */
  defaultFocus?: boolean;
  readOnly?: boolean;
  title?: string;
  /** A control shown next to the title, e.g. re-walk on a newer pack version. */
  action?: ReactNode;
}

function Timeline({
  nodes,
  timeline,
  onSelect,
}: {
  nodes: MapNode[];
  timeline: TimelineItem[];
  onSelect: (nodeId: string) => void;
}) {
  // Earlier choices (now Tried) come first, then the current choice.
  const tried = nodes.filter((n) => n.status === "tried" && !n.result?.response);
  const chosen = nodes.filter((n) => n.status === "chosen");
  if (nodes.length === 0) return null;
  return (
    <ol
      aria-label="Timeline"
      data-testid="timeline"
      className="mt-2 flex items-center gap-2 overflow-x-auto pb-1 text-xs"
    >
      <li className="shrink-0 rounded-full bg-neutral-100 px-2.5 py-1 font-medium">Presented</li>
      {tried.map((n) => (
        <li key={`tried-${n.nodeId}`} className="shrink-0">
          <button
            type="button"
            className="rounded-full bg-neutral-100 px-2.5 py-1"
            onClick={() => onSelect(n.nodeId)}
          >
            Tried {n.label}
          </button>
        </li>
      ))}
      {chosen.map((n) => (
        <li key={`chosen-${n.nodeId}`} className="shrink-0">
          <button
            type="button"
            className="rounded-full bg-teal-100 px-2.5 py-1"
            onClick={() => onSelect(n.nodeId)}
          >
            Chose {n.label}
          </button>
        </li>
      ))}
      {timeline.map((item, i) => (
        <li key={`${item.nodeId}-${i}`} className="shrink-0">
          <button
            type="button"
            className="rounded-full bg-amber-100 px-2.5 py-1"
            onClick={() => onSelect(item.nodeId)}
          >
            {item.label} · {EVENT_WORD[item.kind]}
            {item.value ? ` ${item.value}` : ""}
          </button>
        </li>
      ))}
    </ol>
  );
}

export function GraphCanvas(props: GraphCanvasProps) {
  const { selectedNodeId, onSelectNode } = props;
  const [focus, setFocus] = useState(props.defaultFocus ?? true);
  const visible = useMemo(
    () => (focus ? focusIds(props.nodes, props.edges, selectedNodeId) : null),
    [focus, props.nodes, props.edges, selectedNodeId],
  );
  const nodes = useMemo(
    () => (visible ? props.nodes.filter((n) => visible.has(n.nodeId)) : props.nodes),
    [visible, props.nodes],
  );
  const edges = useMemo(
    () =>
      visible ? props.edges.filter((e) => visible.has(e.from) && visible.has(e.to)) : props.edges,
    [visible, props.edges],
  );
  const positions = useMemo(() => freeLayout(nodes, edges), [nodes, edges]);
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
  const flowEdges: Edge[] = edges.map((edge) => ({
    id: edge.edgeId,
    source: edge.from,
    target: edge.to,
    type: "smoothstep",
    style: EDGE_STYLE[edge.style],
    animated: edge.style === "exploring",
    label: edge.relation === "requires" ? "needs first" : undefined,
    focusable: false,
    selectable: false,
  }));
  const hidden = props.nodes.length - nodes.length;

  return (
    <section
      aria-label={props.title ?? "Graph region used"}
      className="rounded-card border border-neutral-300 bg-white p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">
          {props.title ?? "Care map"}
          {props.version ? (
            <span className="ml-2 font-mono text-xs font-normal text-ink-quiet">
              {props.version}
              {props.readOnly ? " · read-only replay" : ""}
            </span>
          ) : null}
        </h2>
        {props.action}
        <button
          type="button"
          aria-pressed={focus}
          onClick={() => setFocus((f) => !f)}
          className="rounded border border-neutral-300 px-2 py-1 text-xs"
        >
          {focus
            ? `Focus view${hidden > 0 ? ` · ${hidden} hidden` : ""} — show whole map`
            : "Whole map — focus on now"}
        </button>
        <ul className="flex w-full flex-wrap gap-3 text-[11px] text-ink-quiet" aria-label="Legend">
          {(Object.keys(KIND_LABEL) as NodeKind[]).map((kind) => (
            <li key={kind} className="flex items-center gap-1">
              <span className={cn("inline-block h-2.5 w-2.5 rounded-full", KIND_DOT[kind])} />
              {KIND_LABEL[kind]}
            </li>
          ))}
          <li>Now · To do first · Due · Watch for · Present · Option · Chosen · Tried · Done</li>
        </ul>
      </div>
      <div
        role="application"
        aria-label="Care map: use arrow keys to move between nodes, Enter to open one"
        className="relative h-[calc(100vh-300px)] min-h-[460px] w-full overflow-hidden rounded border border-neutral-200"
      >
        {props.nodes.length === 0 ? (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-ink-quiet">
            The map fills in as Brahma walks
          </p>
        ) : null}
        <ReactFlow
          key={`${props.version}-${focus}-${nodes.map((n) => n.nodeId).join(",")}`}
          nodes={mapNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1 }}
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
      <Timeline nodes={props.nodes} timeline={props.timeline ?? []} onSelect={onSelectNode} />
    </section>
  );
}
