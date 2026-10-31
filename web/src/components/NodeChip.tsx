import { cn } from "@/lib/utils";

/** A citation chip naming a graph node, e.g. "IBD-N4". Decorative inside a line button. */
export function NodeChip({ nodeId, explore = false }: { nodeId: string; explore?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded border px-1.5 py-px font-mono text-[11px]",
        explore ? "border-explore text-explore" : "border-brand-700 text-brand-700",
      )}
      data-node-chip={nodeId}
    >
      <span className="sr-only">source </span>
      {nodeId}
    </span>
  );
}
