// The consultation chat: doctor messages, Brahma's forms, checked lines under fixed section
// headers, the summary and progress (BR3.1–BR3.4). Answer text comes only from line items.

import { useEffect, useRef, type ReactNode } from "react";
import { NodeChip } from "@/components/NodeChip";
import { ChatForm } from "@/components/ChatForm";
import { WalkSummary } from "@/components/WalkSummary";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  PROGRESS_LABELS,
  type ChatItem,
  type WalkState,
  type WorkspaceStatus,
} from "@/state/walkReducer";

type LineItem = Extract<ChatItem, { kind: "line" }>;
type FormItem = Extract<ChatItem, { kind: "form" }>;

export function ChatLine({
  line,
  selected,
  onSelect,
}: {
  line: LineItem;
  selected: boolean;
  onSelect: (line: LineItem) => void;
}) {
  return (
    <button
      type="button"
      data-line-id={line.id}
      aria-pressed={selected}
      onClick={() => onSelect(line)}
      className={cn(
        "flex w-full items-start justify-between gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700",
        selected && "bg-brand-50 ring-2 ring-brand-200",
        line.laneId && "border-l-2 border-dashed border-explore",
      )}
    >
      <span>{line.text}</span>
      <span className="flex flex-wrap gap-1">
        {line.nodeIds.map((id) => (
          <NodeChip key={id} nodeId={id} explore={Boolean(line.laneId)} />
        ))}
      </span>
    </button>
  );
}

const WORKING: ReadonlySet<WorkspaceStatus> = new Set(["working", "exploring"]);

export interface ChatThreadProps {
  state: WalkState;
  status: WorkspaceStatus;
  readOnly: boolean;
  selectedLineIds: ReadonlySet<string>;
  onSelectLine: (line: LineItem) => void;
  onSubmitForm: (form: FormItem, values: Record<string, unknown>, summary: string) => void;
  onCancelForm: (form: FormItem) => void;
  onRetry: () => void;
  onRewalk: () => void;
  onSuggest: () => void;
  onStopExplore: (laneId: string) => void;
  doctorName: string;
}

export function ChatThread(props: ChatThreadProps) {
  const { state, status, readOnly } = props;
  const end = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "nearest" });
  }, [state.items.length, state.progress]);

  const openLaneIds = new Set(Object.values(state.openLanes).filter((lane) => lane !== "pending"));

  return (
    <div className="space-y-3" aria-live="polite" aria-relevant="additions">
      <BrahmaSays>
        Hi {props.doctorName}, I&apos;m Brahma. Tell me about the patient: case history, symptoms
        with how long they&apos;ve lasted, and any results with values and units. No names or IDs.
      </BrahmaSays>
      {state.items.map((item) => {
        switch (item.kind) {
          case "doctor":
            return (
              <div key={item.id} className="flex justify-end">
                <p className="max-w-[85%] rounded-card bg-neutral-200 px-3 py-2 text-sm">
                  {item.text}
                </p>
              </div>
            );
          case "form":
            return (
              <ChatForm
                key={item.id}
                formKind={item.formKind}
                fields={item.fields}
                state={item.state}
                summary={item.summary}
                disabled={readOnly}
                onSubmit={(values, summary) => props.onSubmitForm(item, values, summary)}
                onCancel={item.nodeId ? () => props.onCancelForm(item) : undefined}
              />
            );
          case "header":
            return (
              <div key={item.id} className="flex items-center justify-between pt-1">
                <h3
                  className={cn(
                    "text-xs font-semibold uppercase tracking-wide",
                    item.laneId ? "text-explore" : "text-ink-quiet",
                  )}
                >
                  {item.title}
                </h3>
                {item.laneId && openLaneIds.has(item.laneId) ? (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={readOnly}
                    onClick={() => props.onStopExplore(item.laneId!)}
                  >
                    Stop exploring
                  </Button>
                ) : null}
              </div>
            );
          case "line":
            return (
              <ChatLine
                key={item.id}
                line={item}
                selected={props.selectedLineIds.has(item.id)}
                onSelect={props.onSelectLine}
              />
            );
          case "summary":
            return (
              <WalkSummary
                key={item.id}
                info={item.info}
                disabled={readOnly}
                onRewalk={props.onRewalk}
                onSuggest={props.onSuggest}
              />
            );
          case "notice":
            return (
              <p key={item.id} className="text-center text-xs text-ink-quiet">
                {item.text}
              </p>
            );
          default:
            return null;
        }
      })}
      {WORKING.has(status) ? (
        <p role="status" className="text-sm text-ink-quiet" aria-busy="true">
          <span aria-hidden="true">⟳ </span>
          {state.progress ? PROGRESS_LABELS[state.progress] : "Working"}…
        </p>
      ) : null}
      {status === "error" && state.error ? (
        <div role="alert" className="rounded-card border border-result-bad bg-white p-3 text-sm">
          <p>
            <span aria-hidden="true">! </span>
            {state.error.message}
          </p>
          <p className="text-xs text-ink-quiet">Your entries are kept.</p>
          {state.error.retryable || state.walkId ? (
            <Button className="mt-2" size="sm" disabled={readOnly} onClick={props.onRetry}>
              Retry
            </Button>
          ) : null}
        </div>
      ) : null}
      <div ref={end} />
    </div>
  );
}

function BrahmaSays({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2">
      <span
        aria-hidden="true"
        className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-brand-900 text-xs text-white"
      >
        B
      </span>
      <p className="rounded-card border border-neutral-200 bg-white px-3 py-2 text-sm">
        {children}
      </p>
    </div>
  );
}
