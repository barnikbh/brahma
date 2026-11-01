// Browse a pack's saved nodes (no model): search, grouped list, node detail and a walk
// through connected nodes with a breadcrumb trail. Read-only.

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "@/api/client";
import type { BrowseDetail, BrowseNode, PackGraph, PackInfo } from "@/api/types";
import { Banner } from "@/components/Banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { formatDoseBands, formatWhen } from "@/lib/utils";

const COLUMNS = ["findings", "diagnosis", "tests", "subtype", "treatment", "monitor"];

function show(value: unknown, key?: string): string {
  if (value === null || value === undefined) return "—";
  if (key === "doseBands") return formatDoseBands(value).join("; ");
  if (Array.isArray(value)) return value.join(", ");
  return typeof value === "string" ? value : JSON.stringify(value);
}

export function updatedLine(detail: BrowseDetail): string {
  if (!detail.updated) return `Initial pack v${detail.initialVersion}`;
  const { updatedByName, updatedAt, version } = detail.updated;
  const pack = detail.packVersion.split(" ")[0];
  return `Last updated by ${updatedByName} on ${formatWhen(updatedAt)} (${pack} v${version})`;
}

export interface BrowsePanelProps {
  pack: string;
  onPack: (pack: string) => void;
  initialNode?: string;
  onUpdateNode: (node: BrowseNode) => void;
}

export function BrowsePanel({ pack, onPack, initialNode, onUpdateNode }: BrowsePanelProps) {
  const [packs, setPacks] = useState<PackInfo[]>([]);
  const [version, setVersion] = useState("");
  const [graph, setGraph] = useState<PackGraph | null>(null);
  const [query, setQuery] = useState("");
  const [trail, setTrail] = useState<string[]>(initialNode ? [initialNode] : []);
  const [detail, setDetail] = useState<BrowseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentId = trail[trail.length - 1] ?? null;

  const loadGraph = useCallback(async () => {
    setError(null);
    try {
      const [p, g] = await Promise.all([api.packs(), api.graph(pack, version || undefined)]);
      setPacks(p.packs);
      setGraph(g);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The saved nodes could not be loaded.");
    }
  }, [pack, version]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    if (!currentId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setError(null);
    api
      .browseNode(currentId, pack, version || undefined)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof ApiError ? e.message : "The node could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [currentId, pack, version]);

  const byId = useMemo(() => new Map((graph?.nodes ?? []).map((n) => [n.nodeId, n])), [graph]);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (graph?.nodes ?? []).filter(
      (n) => !q || n.label.toLowerCase().includes(q) || n.nodeId.toLowerCase().includes(q),
    );
  }, [graph, query]);
  const groups = COLUMNS.map((column) => ({
    column,
    nodes: matches.filter((n) => n.column === column),
  })).filter((g) => g.nodes.length > 0);

  const open = (nodeId: string) => setTrail((t) => [...t, nodeId]);
  const livePack = packs.find((p) => p.pack === pack);

  return (
    <section aria-label="Browse saved nodes" className="space-y-3 text-sm">
      <div className="grid grid-cols-[110px_110px_1fr] gap-2">
        <label>
          Pack
          <Select
            value={pack}
            onChange={(e) => {
              onPack(e.target.value);
              setVersion("");
              setTrail([]);
            }}
          >
            {(packs.length ? packs.map((p) => p.pack) : [pack]).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Select>
        </label>
        <label>
          Version
          <Select value={version} onChange={(e) => setVersion(e.target.value)}>
            <option value="">Live{livePack ? ` (${livePack.liveVersion})` : ""}</option>
            {(livePack?.versions ?? []).map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </Select>
        </label>
        <label>
          Search nodes
          <Input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name or node ID"
          />
        </label>
      </div>
      {error ? (
        <Banner
          role="alert"
          actions={
            <Button size="sm" variant="outline" onClick={() => void loadGraph()}>
              Retry
            </Button>
          }
        >
          {error}
        </Banner>
      ) : null}
      {currentId ? (
        <NodeDetailView
          detail={detail}
          trail={trail}
          labelOf={(id) => byId.get(id)?.label ?? id}
          onOpen={open}
          onBack={() => setTrail((t) => t.slice(0, -1))}
          onJump={(index) => setTrail((t) => t.slice(0, index + 1))}
          onClose={() => setTrail([])}
          onUpdate={() => {
            const node = byId.get(currentId);
            if (node) onUpdateNode(node);
          }}
        />
      ) : null}
      {!graph ? (
        <p role="status" className="text-ink-quiet">
          Loading nodes…
        </p>
      ) : (
        <div aria-label="Nodes by column" className="space-y-3">
          {groups.length === 0 ? <p className="text-ink-quiet">No nodes match.</p> : null}
          {groups.map((g) => (
            <div key={g.column}>
              <h3 className="text-xs font-semibold uppercase text-ink-quiet">
                {g.column} ({g.nodes.length})
              </h3>
              <ul className="mt-1 space-y-0.5">
                {g.nodes.map((n) => (
                  <li key={n.nodeId}>
                    <button
                      type="button"
                      aria-current={n.nodeId === currentId ? "true" : undefined}
                      onClick={() => setTrail([n.nodeId])}
                      className="flex w-full items-center gap-2 rounded px-2 py-1 text-left hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
                    >
                      <span className="font-mono text-xs text-ink-quiet">{n.nodeId}</span>
                      <span className="truncate">{n.label}</span>
                      <Badge variant="quiet" className="ml-auto">
                        {n.type}
                      </Badge>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function NodeDetailView({
  detail,
  trail,
  labelOf,
  onOpen,
  onBack,
  onJump,
  onClose,
  onUpdate,
}: {
  detail: BrowseDetail | null;
  trail: string[];
  labelOf: (nodeId: string) => string;
  onOpen: (nodeId: string) => void;
  onBack: () => void;
  onJump: (index: number) => void;
  onClose: () => void;
  onUpdate: () => void;
}) {
  // A weight-band node's doseValue is only its first band, so the bands stand alone.
  const fields = Object.entries(detail?.node.fields ?? {}).filter(
    ([k]) =>
      detail?.node.fields.doseBasis !== "weight_band" || !["doseValue", "doseUnit"].includes(k),
  );
  return (
    <article
      aria-label="Node detail"
      className="space-y-2 rounded-card border-2 border-brand-900 p-3"
    >
      <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-xs">
        {trail.map((id, i) => (
          <span key={`${id}-${i}`} className="flex items-center gap-1">
            {i > 0 ? <span aria-hidden="true">›</span> : null}
            {i === trail.length - 1 ? (
              <span aria-current="page" className="font-semibold">
                {labelOf(id)}
              </span>
            ) : (
              <button type="button" className="text-brand-700 underline" onClick={() => onJump(i)}>
                {labelOf(id)}
              </button>
            )}
          </span>
        ))}
      </nav>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={trail.length < 2} onClick={onBack}>
          Back
        </Button>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Close
        </Button>
        {detail ? (
          <Button size="sm" className="ml-auto" onClick={onUpdate}>
            Update this node
          </Button>
        ) : null}
      </div>
      {!detail ? (
        <p role="status" className="text-ink-quiet">
          Loading node…
        </p>
      ) : (
        <>
          <h3 className="font-serif text-lg text-brand-900">{detail.node.label}</h3>
          <p className="flex flex-wrap gap-2">
            <Badge variant="quiet">{detail.node.type}</Badge>
            <span className="font-mono text-xs">{detail.node.nodeId}</span>
          </p>
          <p data-testid="updated-line" className="text-xs text-ink-quiet">
            {updatedLine(detail)}
            {detail.updated ? `, approved by ${detail.updated.approvedByName}` : ""}
          </p>
          <p>{detail.node.content}</p>
          {fields.length > 0 ? (
            <dl className="grid grid-cols-[130px_1fr] gap-x-2 gap-y-0.5">
              {fields.map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-ink-quiet">{k}</dt>
                  <dd>{show(v, k)}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          <Connections title="Leads to" items={detail.outgoing} onOpen={onOpen} />
          <Connections title="Reached from" items={detail.incoming} onOpen={onOpen} />
          <section aria-label="Sources">
            <h4 className="font-semibold">Sources</h4>
            <ul className="mt-1 space-y-0.5">
              {detail.sources.map((s) => (
                <li key={s.sourceId}>
                  {s.url ? (
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-brand-700 underline"
                    >
                      {s.title}
                    </a>
                  ) : (
                    s.title
                  )}{" "}
                  <span className="text-ink-quiet">
                    ({s.year}) · {s.section}
                  </span>
                </li>
              ))}
            </ul>
          </section>
          {detail.comments.length > 0 ? (
            <section aria-label="Comments">
              <h4 className="font-semibold">Comments</h4>
              <ul className="mt-1 space-y-0.5 text-xs">
                {detail.comments.map((c) => (
                  <li key={c.commentId}>
                    <span className="text-ink-quiet">{c.authorProfileId}: </span>
                    {c.text}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </article>
  );
}

function Connections({
  title,
  items,
  onOpen,
}: {
  title: string;
  items: BrowseDetail["outgoing"];
  onOpen: (nodeId: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <section aria-label={title}>
      <h4 className="font-semibold">{title}</h4>
      <ul className="mt-1 space-y-0.5">
        {items.map((n) => (
          <li key={n.edgeId}>
            <span className="text-xs text-ink-quiet">{n.relationLabel}: </span>
            <button
              type="button"
              onClick={() => onOpen(n.nodeId)}
              className="text-brand-700 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
            >
              {n.label}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
