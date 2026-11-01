// One drafted node in a proposal: a new node in full, or the changed values of an existing
// node as a before and after with word-level highlights, always with its cited source.

import { NodeChip } from "@/components/NodeChip";
import { Badge } from "@/components/ui/badge";
import type { ProposalChange, Source } from "@/api/types";
import { formatDoseBands, wordDiff, type DiffPart } from "@/lib/utils";

const LABELS: Record<string, string> = {
  label: "Name",
  content: "Summary",
  drug: "Drug",
  route: "Route",
  dose: "Dose",
  frequency: "Frequency",
  duration: "Duration",
  rounding: "Rounding",
  drugClass: "Drug class",
  contraindications: "Contraindications",
};
const DOSE_KEYS = new Set(["doseValue", "doseUnit", "doseBasis", "doseBands"]);
// A new node takes the rest from its neighbour; these are what a reviewer needs to read.
const NEW_NODE_ROWS = ["content", "drug", "route", "dose", "frequency", "duration"];

function humanise(key: string): string {
  const words = key.replace(/([A-Z])/g, " $1").toLowerCase();
  return LABELS[key] ?? words.charAt(0).toUpperCase() + words.slice(1);
}

function display(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.join(", ");
  return typeof value === "string" ? value : JSON.stringify(value);
}

function doseText(fields: Record<string, unknown>): string | null {
  if (fields.doseBasis === "weight_band") return formatDoseBands(fields.doseBands).join("; ");
  if (fields.doseValue === undefined) return null;
  const unit = display(fields.doseUnit ?? "");
  return `${display(fields.doseValue)} ${unit}${fields.doseBasis === "per_kg" ? " per kg" : ""}`;
}

/** A node as readable name-value rows, with the dose fields folded into one "dose" row. */
function nodeRows(node: Record<string, unknown> | null | undefined): Record<string, string> {
  if (!node) return {};
  const fields = (node.fields ?? {}) as Record<string, unknown>;
  const rows: Record<string, string> = {};
  for (const key of ["label", "content"]) {
    if (node[key] !== undefined) rows[key] = display(node[key]);
  }
  const dose = doseText(fields);
  if (dose) rows.dose = dose;
  for (const [key, value] of Object.entries(fields)) {
    if (!DOSE_KEYS.has(key)) rows[key] = display(value);
  }
  return rows;
}

function DiffText({ parts, kind }: { parts: DiffPart[]; kind: "before" | "after" }) {
  return (
    <>
      {parts.map((part, i) => {
        if (part.kind === "same") return <span key={i}>{part.text}</span>;
        if (kind === "before" && part.kind === "removed") {
          return (
            <del key={i} className="rounded-sm bg-red-100 text-result-bad">
              {part.text}
            </del>
          );
        }
        if (kind === "after" && part.kind === "added") {
          return (
            <ins
              key={i}
              className="rounded-sm bg-green-100 font-medium text-result-ok no-underline"
            >
              {part.text}
            </ins>
          );
        }
        return null;
      })}
    </>
  );
}

function DoseTable({ bands }: { bands: string[] }) {
  return (
    <ul data-testid="dose-bands" className="space-y-0.5">
      {bands.map((band) => (
        <li key={band} className="font-medium">
          {band}
        </li>
      ))}
    </ul>
  );
}

function NewNode({ change }: { change: ProposalChange }) {
  const rows = nodeRows(change.after);
  const fields = (change.after.fields ?? {}) as Record<string, unknown>;
  const bands = fields.doseBasis === "weight_band" ? formatDoseBands(fields.doseBands) : null;
  return (
    <dl className="grid grid-cols-[92px_1fr] gap-x-3 gap-y-1 rounded border border-green-300 bg-green-50 p-3">
      {NEW_NODE_ROWS.filter((key) => rows[key]).map((key) => (
        <div key={key} className="contents">
          <dt className="text-ink-quiet">{humanise(key)}</dt>
          <dd>{key === "dose" && bands ? <DoseTable bands={bands} /> : rows[key]}</dd>
        </div>
      ))}
    </dl>
  );
}

function ChangedNode({ change, baseVersion }: { change: ProposalChange; baseVersion: string }) {
  const before = nodeRows(change.before);
  const after = nodeRows(change.after);
  const keys = Object.keys(after).filter((key) => after[key] !== before[key]);
  if (keys.length === 0) return <p className="text-ink-quiet">Only the citation changes.</p>;
  return (
    <div className="space-y-2">
      {keys.map((key) => {
        const parts = wordDiff(before[key] ?? "", after[key]);
        return (
          <div key={key}>
            <h4 className="text-xs font-semibold uppercase text-ink-quiet">{humanise(key)}</h4>
            <div className="mt-0.5 grid grid-cols-2 gap-2">
              <p
                aria-label={`${humanise(key)} before`}
                className="rounded border border-neutral-200 p-2"
              >
                <span className="sr-only">Before {baseVersion}: </span>
                <DiffText parts={parts} kind="before" />
              </p>
              <p
                aria-label={`${humanise(key)} after`}
                className="rounded border border-green-300 p-2"
              >
                <span className="sr-only">After: </span>
                <DiffText parts={parts} kind="after" />
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Citation({ change, source }: { change: ProposalChange; source?: Source }) {
  const url = change.sourceUrl ?? source?.url;
  if (!url && !change.sourcePassage) return null;
  return (
    <section aria-label="Source" className="rounded border-l-2 border-brand-700 bg-brand-50 p-2">
      <h4 className="text-xs font-semibold uppercase text-ink-quiet">Source</h4>
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="break-words text-brand-700 underline"
        >
          {source?.title ?? url}
        </a>
      ) : null}
      {source ? (
        <p className="text-xs text-ink-quiet">
          {source.sourceId} · {source.section}
        </p>
      ) : null}
      {change.sourcePassage ? (
        <blockquote className="mt-1 whitespace-pre-line text-xs italic">
          {change.sourcePassage}
        </blockquote>
      ) : null}
    </section>
  );
}

export function NodeChange({
  change,
  baseVersion,
  source,
  reachedFrom,
  actions,
}: {
  change: ProposalChange;
  baseVersion: string;
  source?: Source;
  reachedFrom: string[];
  actions?: React.ReactNode;
}) {
  const isNew = change.before === null || change.before === undefined;
  const label = change.after.label ?? change.before?.label;
  return (
    <div data-testid={`node-change-${change.nodeId}`} className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={isNew ? "ok" : "brand"}>{isNew ? "New node" : "Updated"}</Badge>
        <NodeChip nodeId={change.nodeId} />
        {label ? <span className="font-semibold">{display(label)}</span> : null}
        {actions ? <span className="ml-auto">{actions}</span> : null}
      </div>
      {isNew ? (
        <NewNode change={change} />
      ) : (
        <ChangedNode change={change} baseVersion={baseVersion} />
      )}
      {isNew && reachedFrom.length > 0 ? (
        <p className="flex flex-wrap items-center gap-1 text-xs text-ink-quiet">
          Offered from{" "}
          {reachedFrom.map((id) => (
            <NodeChip key={id} nodeId={id} />
          ))}
        </p>
      ) : null}
      <Citation change={change} source={source} />
      {change.copyFlag ? (
        <p className="text-result-bad" data-testid="copy-flag">
          <span aria-hidden="true">! </span>Possible verbatim copy — publish blocked
        </p>
      ) : null}
    </div>
  );
}
