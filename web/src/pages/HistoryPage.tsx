// Screen 16: session history with filters, the audit detail, a read-only replay on the
// session's own version, and JSON / PDF export (BR5).

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "@/api/client";
import type { Outcome, SessionDetail as Detail, SessionSummary } from "@/api/types";
import { Banner } from "@/components/Banner";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodeChip } from "@/components/NodeChip";
import { Synthetic } from "@/components/Synthetic";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { formatWhen } from "@/lib/utils";

const OUTCOME: Record<Outcome, { label: string; variant: BadgeProps["variant"] }> = {
  answered: { label: "✓ Answered", variant: "ok" },
  needs_data: { label: "? Needs data", variant: "pending" },
  out_of_knowledge: { label: "⊘ Out of knowledge", variant: "quiet" },
  error: { label: "! Error", variant: "bad" },
};

export function OutcomeChip({ outcome }: { outcome: Outcome }) {
  const look = OUTCOME[outcome] ?? OUTCOME.error;
  return <Badge variant={look.variant}>{look.label}</Badge>;
}

export function HistoryPage() {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();
  const [outcome, setOutcome] = useState<Outcome | "">("");
  const [q, setQ] = useState("");
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setSessions((await api.sessions({ outcome, q })).sessions);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "History failed to load.");
    }
  }, [outcome, q]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  const filtered = Boolean(outcome || q.trim());

  return (
    <section aria-labelledby="history-title" className="space-y-3">
      <h1 id="history-title" className="font-serif text-2xl text-brand-900">
        Session history
      </h1>
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Outcome
          <Select value={outcome} onChange={(e) => setOutcome(e.target.value as Outcome | "")}>
            <option value="">All outcomes</option>
            <option value="answered">Answered</option>
            <option value="needs_data">Needs data</option>
            <option value="out_of_knowledge">Out of knowledge</option>
            <option value="error">Error</option>
          </Select>
        </label>
        <label className="text-sm">
          Search
          <Input
            type="search"
            value={q}
            maxLength={200}
            placeholder="Case ID or diagnosis"
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
      </div>
      {error ? (
        <Banner
          role="alert"
          actions={
            <Button size="sm" variant="outline" onClick={() => void load()}>
              Retry
            </Button>
          }
        >
          {error}
        </Banner>
      ) : null}
      <div className="grid grid-cols-[minmax(360px,1fr)_2fr] gap-4">
        <div>
          {sessions === null && !error ? (
            <p role="status" className="text-sm text-ink-quiet">
              Loading sessions…
            </p>
          ) : null}
          {sessions && sessions.length === 0 ? (
            <p className="rounded-card border border-neutral-300 bg-white p-4 text-center">
              {filtered ? "No sessions match these filters" : "No sessions yet"}
            </p>
          ) : null}
          {sessions && sessions.length > 0 ? (
            <ul
              aria-label="Sessions"
              className="divide-y divide-neutral-200 rounded-card border border-neutral-300 bg-white"
            >
              {sessions.map((s) => (
                <li key={s.sessionId}>
                  <button
                    type="button"
                    aria-current={s.sessionId === sessionId}
                    onClick={() => navigate(`/history/${s.sessionId}`)}
                    className="flex w-full flex-col gap-1 px-3 py-2 text-left hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 aria-[current=true]:bg-brand-50"
                  >
                    <span className="flex items-center gap-2">
                      <span className="font-mono text-xs">{s.sessionId}</span>
                      <OutcomeChip outcome={s.outcome} />
                      <span className="ml-auto text-xs text-ink-quiet">
                        {formatWhen(s.createdAt)}
                      </span>
                    </span>
                    <span className="text-sm">{s.label}</span>
                    <span className="text-xs text-ink-quiet">
                      <Synthetic>{s.caseId}</Synthetic> · {s.packVersion}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
        <div>
          {sessionId ? (
            <SessionDetail sessionId={sessionId} />
          ) : (
            <p className="text-sm text-ink-quiet">Pick a session to see its audit and replay.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export function SessionDetail({ sessionId }: { sessionId: string }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    setDetail(null);
    try {
      setDetail(await api.sessionDetail(sessionId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The session failed to load.");
    }
  }, [sessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <Banner
        role="alert"
        actions={
          <Button size="sm" variant="outline" onClick={() => void load()}>
            Retry
          </Button>
        }
      >
        {error}
      </Banner>
    );
  }
  if (!detail) {
    return (
      <p role="status" className="text-sm text-ink-quiet">
        Loading session…
      </p>
    );
  }
  const { record } = detail;
  const counts = record.answer.counts ?? {};
  return (
    <article aria-label={`Session ${record.sessionId}`} className="space-y-3">
      <div className="rounded-card border border-neutral-300 bg-white p-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">Session {record.sessionId}</h2>
          <OutcomeChip outcome={record.outcome} />
          <Badge className="font-mono">{record.packVersion}</Badge>
          <Badge variant="quiet">
            Model: {record.provider} · {record.model}
          </Badge>
          <span className="ml-auto flex gap-2">
            <Button asChild size="sm" variant="outline">
              <a href={api.exportUrl(record.sessionId, "json")} download>
                Export JSON
              </a>
            </Button>
            <Button asChild size="sm" variant="outline">
              <a href={api.exportUrl(record.sessionId, "pdf")} download>
                Export PDF
              </a>
            </Button>
          </span>
        </div>
        <p className="mt-2 text-xs text-ink-quiet">
          Case <Synthetic>{record.caseId}</Synthetic> · {formatWhen(record.createdAt)} ·{" "}
          {detail.disclaimer}
        </p>
        <h3 className="mt-3 text-xs font-semibold uppercase text-ink-quiet">Inputs</h3>
        <p>{record.inputs.text}</p>
        <h3 className="mt-3 text-xs font-semibold uppercase text-ink-quiet">Answer</h3>
        <p className="font-medium">{record.answer.summary}</p>
        <p className="text-xs">
          {counts.steps ?? 0} steps · {counts.cited ?? 0} cited · {counts.ungrounded ?? 0}{" "}
          ungrounded
        </p>
        {record.answer.sections.map((section) => (
          <div key={section.sectionId} className="mt-2">
            <h4 className="text-xs font-semibold uppercase text-ink-quiet">{section.title}</h4>
            <ul>
              {section.lines.map((line, i) => (
                <li key={i} className="flex justify-between gap-2">
                  <span>{line.text}</span>
                  <span className="flex gap-1">
                    {line.nodeIds.map((id) => (
                      <NodeChip key={id} nodeId={id} />
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {record.explanation.length > 0 ? (
          <div className="mt-2">
            <h4 className="text-xs font-semibold uppercase text-ink-quiet">Why</h4>
            <ul>
              {record.explanation.map((line, i) => (
                <li key={i} className="flex justify-between gap-2">
                  <span>{line.text}</span>
                  <span className="flex gap-1">
                    {line.nodeIds.map((id) => (
                      <NodeChip key={id} nodeId={id} />
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <GraphCanvas
        defaultFocus={false}
        title="Replay"
        readOnly
        nodes={detail.map.nodes}
        edges={detail.map.edges}
        version={detail.map.version}
        order={detail.map.selectedPath}
        selectedNodeId={selected}
        onSelectNode={setSelected}
      />
      <div className="rounded-card border border-neutral-300 bg-white p-4 text-sm">
        <h3 className="font-semibold">Audit entries</h3>
        <ul className="mt-1 space-y-0.5 font-mono text-xs">
          {detail.entries.map((entry) => (
            <li key={entry.entryId}>
              {formatWhen(entry.createdAt)} · {entry.kind}
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
