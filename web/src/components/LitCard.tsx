// What a step on the map newly lit, with one cited line or two from the model (written
// from those nodes only and checked by the grounding guard before it gets here).

import { NodeChip } from "@/components/NodeChip";
import type { ChatItem } from "@/state/walkReducer";

type Lit = Extract<ChatItem, { kind: "lit" }>;

export function LitCard({ item }: { item: Lit }) {
  return (
    <div
      data-testid="lit-card"
      className="space-y-1 rounded-card border border-neutral-200 bg-white px-3 py-2 text-sm"
    >
      <p className="text-xs text-ink-quiet">{item.notice}</p>
      {item.items.length > 0 ? (
        <>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
            Now lit on the map
          </p>
          <ul className="space-y-1">
            {item.items.map((n) => (
              <li key={n.nodeId} className="flex items-start justify-between gap-3">
                <span>{n.label}</span>
                <NodeChip nodeId={n.nodeId} />
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {item.pending ? (
        <p role="status" className="text-xs text-ink-quiet">
          Writing a cited note…
        </p>
      ) : null}
      {item.lines.map((line) => (
        <p key={line.text}>
          {line.text}{" "}
          {line.nodeIds.map((id) => (
            <NodeChip key={id} nodeId={id} />
          ))}
        </p>
      ))}
    </div>
  );
}
