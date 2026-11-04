// The next steps after a drug choice: dose, review, monitor, watch-outs and the
// next tier, every row cited. All labels come from the walked graph.

import { NodeChip } from "@/components/NodeChip";
import type { TraversePath, TraversePathItem } from "@/api/types";

function PathRow({ items }: { items: TraversePathItem[] }) {
  return (
    <ul className="mt-1 space-y-1">
      {items.map((item) => (
        <li key={item.nodeId} className="flex items-start justify-between gap-3">
          <span>{item.label}</span>
          <NodeChip nodeId={item.nodeId} />
        </li>
      ))}
    </ul>
  );
}

export function PathCard({ path }: { path: TraversePath }) {
  return (
    <div
      data-testid="path-card"
      className="space-y-2 rounded-card border border-neutral-200 bg-white px-3 py-2 text-sm"
    >
      <p>
        <strong>Now on {path.drug.label}</strong> <NodeChip nodeId={path.drug.nodeId} />
      </p>
      {path.review.length > 0 ? (
        <section aria-label="Day-3 review">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
            Day-3 review
          </h4>
          <PathRow items={path.review} />
        </section>
      ) : null}
      {path.monitor.length > 0 ? (
        <section aria-label="Monitor">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">Monitor</h4>
          <PathRow items={path.monitor} />
        </section>
      ) : null}
      {path.watchOuts.length > 0 ? (
        <section aria-label="Watch for">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
            Watch for
          </h4>
          <PathRow items={path.watchOuts} />
        </section>
      ) : null}
      {path.nextTiers.length > 0 ? (
        <section aria-label="If this tier fails">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
            If {path.tier.label} fails
          </h4>
          <PathRow items={path.nextTiers} />
        </section>
      ) : (
        <p className="text-xs text-ink-quiet">No further tier in this pack.</p>
      )}
      <p className="text-xs text-ink-quiet">
        When you know how it went, type the outcome here — for example &quot;steroids work&quot; —
        and I will walk the next tier.
      </p>
    </div>
  );
}
