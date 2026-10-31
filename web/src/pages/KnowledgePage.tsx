// Screen 17: browse saved nodes, update them in a conversation, review proposals (A6) and
// see the version history (BR6, C9).

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, api } from "@/api/client";
import type { Proposal, VersionHistoryEntry } from "@/api/types";
import { Banner } from "@/components/Banner";
import { NodeChip } from "@/components/NodeChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { BrowsePanel } from "@/components/knowledge/BrowsePanel";
import { UpdateChat } from "@/components/knowledge/UpdateChat";
import { formatWhen } from "@/lib/utils";
import { useSession } from "@/state/session";

export function KnowledgePage() {
  const { session, refreshHealth, refresh } = useSession();
  const [params] = useSearchParams();
  const [pack, setPack] = useState(params.get("node")?.split("-")[0] || "IBD");
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [versions, setVersions] = useState<VersionHistoryEntry[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<"browse" | "update">(params.get("node") ? "browse" : "update");
  const [seed, setSeed] = useState<{ text: string; key: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, v] = await Promise.all([api.proposals(), api.versions(pack)]);
      setProposals(p.proposals);
      setVersions(v.versions);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Knowledge failed to load.");
    }
  }, [pack]);

  useEffect(() => {
    void load();
  }, [load]);

  const reviewer = session?.profile.role === "reviewer";
  const current = proposals.find((p) => p.proposalId === selected) ?? null;

  return (
    <section aria-labelledby="knowledge-title" className="space-y-3">
      <h1 id="knowledge-title" className="font-serif text-2xl text-brand-900">
        Knowledge update
      </h1>
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
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-4">
          <div className="rounded-card border border-neutral-300 bg-white p-4">
            <div role="tablist" aria-label="Knowledge actions" className="mb-3 flex gap-2">
              {(["browse", "update"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  role="tab"
                  id={`tab-${t}`}
                  aria-selected={tab === t}
                  aria-controls={`panel-${t}`}
                  onClick={() => setTab(t)}
                  className={`rounded px-3 py-1 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 ${
                    tab === t ? "bg-brand-900 text-white" : "text-brand-900 hover:bg-brand-50"
                  }`}
                >
                  {t === "browse" ? "Browse nodes" : "Update knowledge"}
                </button>
              ))}
            </div>
            <div
              role="tabpanel"
              id="panel-browse"
              aria-labelledby="tab-browse"
              hidden={tab !== "browse"}
            >
              {tab === "browse" ? (
                <BrowsePanel
                  pack={pack}
                  onPack={setPack}
                  initialNode={params.get("node") ?? undefined}
                  onUpdateNode={(node) => {
                    setSeed({
                      text: `Update ${node.label} (${node.nodeId}) from `,
                      key: Date.now(),
                    });
                    setTab("update");
                  }}
                />
              ) : null}
            </div>
            <div
              role="tabpanel"
              id="panel-update"
              aria-labelledby="tab-update"
              hidden={tab !== "update"}
            >
              {tab === "update" ? (
                <UpdateChat
                  pack={pack}
                  seed={seed}
                  onProposal={(p) => {
                    setProposals((all) =>
                      all.some((x) => x.proposalId === p.proposalId) ? all : [p, ...all],
                    );
                    setSelected(p.proposalId);
                    void load();
                  }}
                />
              ) : null}
            </div>
          </div>
          <div className="rounded-card border border-neutral-300 bg-white p-4">
            <h2 className="font-semibold">Proposals</h2>
            {proposals.length === 0 ? (
              <p className="text-sm text-ink-quiet">No proposals yet.</p>
            ) : (
              <ul className="mt-2 space-y-1">
                {proposals.map((p) => (
                  <li key={p.proposalId}>
                    <button
                      type="button"
                      onClick={() => setSelected(p.proposalId)}
                      className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
                    >
                      <span className="font-mono text-xs">
                        {p.pack} {p.baseVersion} → {p.targetVersion}
                      </span>
                      <span className="truncate">{p.comment}</span>
                      <Badge
                        className="ml-auto"
                        variant={p.status === "published" ? "ok" : "quiet"}
                      >
                        {p.status}
                      </Badge>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <div className="space-y-4">
          {current ? (
            <ProposalView
              proposal={current}
              reviewer={reviewer}
              onDecided={(p) => {
                setProposals((all) => all.map((x) => (x.proposalId === p.proposalId ? p : x)));
                void load();
                void refreshHealth();
                void refresh();
              }}
            />
          ) : null}
          <div className="rounded-card border border-neutral-300 bg-white p-4">
            <h2 className="font-semibold">Version history · {pack}</h2>
            {versions.length <= 1 ? (
              <p className="text-sm text-ink-quiet">No versions beyond the first.</p>
            ) : null}
            <table className="mt-2 w-full text-left text-sm">
              <thead className="text-xs uppercase text-ink-quiet">
                <tr>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th>Author</th>
                  <th>Change</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v, i) => (
                  <tr key={`${v.version}-${v.status}-${i}`}>
                    <td className="font-mono">{v.version}</td>
                    <td>{v.status}</td>
                    <td>{formatWhen(v.date)}</td>
                    <td>{v.authorName ?? v.author}</td>
                    <td>{v.change}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

function show(value: unknown): string {
  if (value === null || value === undefined) return "—";
  return typeof value === "string" ? value : JSON.stringify(value);
}

export function ProposalView({
  proposal,
  reviewer,
  onDecided,
}: {
  proposal: Proposal;
  reviewer: boolean;
  onDecided: (proposal: Proposal) => void;
}) {
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const flagged =
    proposal.changes.some((c) => c.copyFlag) || proposal.copyFlaggedNodeIds.length > 0;
  const open = proposal.status === "proposed";

  const decide = async (action: "publish" | "reject") => {
    setError(null);
    try {
      onDecided(
        action === "publish"
          ? await api.publish(proposal.proposalId, comment)
          : await api.reject(proposal.proposalId, comment),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The decision could not be saved.");
    }
  };

  return (
    <article
      aria-label="Proposal review"
      className="space-y-2 rounded-card border-2 border-brand-900 bg-white p-4 text-sm"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold">
          Proposed version {proposal.pack} {proposal.baseVersion} → {proposal.targetVersion}
        </h2>
        <span className="text-ink-quiet">
          proposed by {proposal.proposerName ?? proposal.proposerProfileId} ·{" "}
          {formatWhen(proposal.createdAt)}
        </span>
        <Badge>{proposal.status}</Badge>
      </div>
      <p>
        <span className="text-ink-quiet">Comment: </span>
        {proposal.comment}
      </p>
      {proposal.changes.map((change) => {
        const keys = Object.keys(change.after).filter(
          (k) => show(change.after[k]) !== show(change.before?.[k]),
        );
        return (
          <div key={change.nodeId} className="space-y-1">
            <NodeChip nodeId={change.nodeId} />
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded border border-neutral-200 p-2">
                <h3 className="text-xs font-semibold uppercase text-ink-quiet">
                  Before {proposal.baseVersion}
                </h3>
                {keys.map((k) => (
                  <p key={k}>
                    <span className="text-ink-quiet">{k}: </span>
                    {show(change.before?.[k])}
                  </p>
                ))}
              </div>
              <div className="rounded border border-brand-200 p-2">
                <h3 className="text-xs font-semibold uppercase text-ink-quiet">
                  After {proposal.targetVersion} draft
                </h3>
                {keys.map((k) => (
                  <p key={k}>
                    <span className="text-ink-quiet">{k}: </span>
                    {show(change.after[k])}
                  </p>
                ))}
              </div>
            </div>
            {change.sourceUrl ? (
              <p className="break-all text-xs text-ink-quiet">Source: {change.sourceUrl}</p>
            ) : null}
            {change.sourcePassage ? (
              <p className="italic">Source passage: “{change.sourcePassage}”</p>
            ) : null}
            {change.copyFlag ? (
              <p className="text-result-bad" data-testid="copy-flag">
                <span aria-hidden="true">! </span>Possible verbatim copy — publish blocked
              </p>
            ) : null}
          </div>
        );
      })}
      {proposal.reviewComment ? (
        <p>
          <span className="text-ink-quiet">
            {proposal.status === "published" ? "Published" : "Rejected"} by{" "}
            {proposal.reviewerName ?? proposal.reviewerProfileId}
            {proposal.decidedAt ? ` · ${formatWhen(proposal.decidedAt)}` : ""}:{" "}
          </span>
          {proposal.reviewComment}
        </p>
      ) : null}
      {reviewer && open ? (
        <div className="space-y-2">
          <label className="block">
            Reviewer comment
            <Textarea value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <Button disabled={flagged} onClick={() => void decide("publish")}>
              Publish {proposal.targetVersion}
            </Button>
            <Button
              variant="danger"
              disabled={!comment.trim()}
              onClick={() => void decide("reject")}
            >
              Reject
            </Button>
          </div>
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="text-result-bad">
          ! {error}
        </p>
      ) : null}
    </article>
  );
}
