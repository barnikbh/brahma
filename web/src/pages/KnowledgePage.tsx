// Screen 17: browse saved nodes, update them in a conversation, review proposals (A6) and
// see the version history (BR6, C9).

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError, api } from "@/api/client";
import type { Proposal, VersionHistoryEntry } from "@/api/types";
import { Banner } from "@/components/Banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { BrowsePanel } from "@/components/knowledge/BrowsePanel";
import { NodeChange } from "@/components/knowledge/NodeChange";
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
  const [browseNode, setBrowseNode] = useState(params.get("node") ?? undefined);
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
                  key={browseNode}
                  pack={pack}
                  onPack={setPack}
                  initialNode={browseNode}
                  onUpdateNode={(node) => {
                    setSeed({
                      text: `Update ${node.label} (${node.nodeId})`,
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
                        {p.pack} {p.baseVersion} →{" "}
                        {p.publishedVersion ?? p.targetVersion.replace(" draft", "")}
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
              onOpenNode={(nodeId) => {
                setBrowseNode(nodeId);
                setPack(current?.pack ?? pack);
                setTab("browse");
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

export function ProposalView({
  proposal,
  reviewer,
  onDecided,
  onOpenNode,
}: {
  proposal: Proposal;
  reviewer: boolean;
  onDecided: (proposal: Proposal) => void;
  onOpenNode?: (nodeId: string) => void;
}) {
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deciding, setDeciding] = useState(false);
  const flagged =
    proposal.changes.some((c) => c.copyFlag) || proposal.copyFlaggedNodeIds.length > 0;
  const open = proposal.status === "proposed";
  const target = proposal.publishedVersion ?? proposal.targetVersion.replace(" draft", "");

  const decide = async (action: "publish" | "reject") => {
    setError(null);
    setDeciding(true);
    try {
      onDecided(
        action === "publish"
          ? await api.publish(proposal.proposalId, comment)
          : await api.reject(proposal.proposalId, comment),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The decision could not be saved.");
    } finally {
      setDeciding(false);
    }
  };

  return (
    <article
      aria-label="Proposal review"
      className="space-y-3 rounded-card border-2 border-brand-900 bg-white p-4 text-sm"
    >
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">
            {proposal.pack} {proposal.baseVersion} → {target}
          </h2>
          <Badge variant={proposal.status === "published" ? "ok" : "quiet"}>
            {proposal.status}
          </Badge>
        </div>
        <p>{proposal.comment}</p>
        <p className="text-xs text-ink-quiet">
          Proposed by {proposal.proposerName ?? proposal.proposerProfileId} ·{" "}
          {formatWhen(proposal.createdAt)}
        </p>
      </header>
      {proposal.changes.map((change) => (
        <NodeChange
          key={change.nodeId}
          change={change}
          baseVersion={proposal.baseVersion}
          source={proposal.citedSources?.find((s) => s.url === change.sourceUrl)}
          reachedFrom={(proposal.changeSet?.addEdges ?? [])
            .filter((e) => e.toNodeId === change.nodeId)
            .map((e) => e.fromNodeId)}
          actions={
            proposal.status === "published" && onOpenNode ? (
              <Button size="sm" variant="outline" onClick={() => onOpenNode(change.nodeId)}>
                Open node
              </Button>
            ) : undefined
          }
        />
      ))}
      {proposal.status === "published" ? (
        <p role="status" className="font-medium text-result-ok">
          ✓ Live in {proposal.pack} {proposal.publishedVersion}
          {proposal.decidedAt ? ` · ${formatWhen(proposal.decidedAt)}` : ""}
        </p>
      ) : null}
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
      {open && !reviewer ? (
        <p role="status" className="text-result-pending">
          ? Waiting for a clinical reviewer to approve. Nothing is live yet.
        </p>
      ) : null}
      {reviewer && open ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Button disabled={flagged || deciding} onClick={() => void decide("publish")}>
              Approve and publish {target}
            </Button>
            <Button
              variant="danger"
              disabled={!comment.trim() || deciding}
              onClick={() => void decide("reject")}
            >
              Reject
            </Button>
          </div>
          <label className="block text-xs text-ink-quiet">
            Comment (optional to approve, needed to reject)
            <Textarea value={comment} onChange={(e) => setComment(e.target.value)} />
          </label>
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
