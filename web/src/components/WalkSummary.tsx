import { Link } from "react-router-dom";
import { DISCLAIMER } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { packChips } from "@/lib/utils";
import type { SummaryInfo } from "@/state/walkReducer";

/** Screen 08 summary and A1: counts, pack, model, held-back notice; 3f out of knowledge. */
export function WalkSummary({
  info,
  onRewalk,
  onSuggest,
  disabled,
}: {
  info: SummaryInfo;
  onRewalk?: () => void;
  onSuggest?: () => void;
  disabled?: boolean;
}) {
  const pack = info.packVersion ? packChips(info.packVersion).join(", ") : null;
  const outOfKnowledge = info.outcome === "out_of_knowledge";
  const ungrounded = info.counts?.ungrounded ?? 0;
  return (
    <article
      aria-label="Walk summary"
      className="rounded-card border border-neutral-300 bg-white p-3"
      data-testid="walk-summary"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">Pathway</h3>
        {pack ? <Badge className="font-mono">{pack}</Badge> : null}
        {info.provider ? (
          <Badge variant="quiet">
            Model: {info.provider}
            {info.model ? ` · ${info.model}` : ""}
          </Badge>
        ) : null}
      </div>
      {outOfKnowledge ? (
        <div className="mt-2">
          <p className="font-semibold">
            <span aria-hidden="true">⊘ </span>No grounded answer
          </p>
          <p className="text-sm text-ink-quiet">
            The knowledge graph has no branch for these findings, so Brahma says nothing about them.
          </p>
          {onSuggest ? (
            <Button className="mt-2" variant="outline" size="sm" onClick={onSuggest}>
              Suggest adding this branch
            </Button>
          ) : null}
        </div>
      ) : info.summary ? (
        <p className="mt-2 font-medium">{info.summary}</p>
      ) : null}
      {info.outcome === "needs_data" ? (
        <p className="mt-1 text-sm">
          <span aria-hidden="true">? </span>Some tests are still needed before the plan is complete.
        </p>
      ) : null}
      {info.counts ? (
        <div className="mt-2 flex flex-wrap gap-2" data-testid="walk-counts">
          <Badge variant="default">{info.counts.steps} steps</Badge>
          <Badge variant="brand">✓ {info.counts.cited} cited</Badge>
          <Badge variant={ungrounded > 0 ? "pending" : "default"}>{ungrounded} ungrounded</Badge>
        </div>
      ) : null}
      {ungrounded > 0 ? (
        <p className="mt-2 text-sm">
          <span aria-hidden="true">! </span>
          {ungrounded} {ungrounded === 1 ? "line" : "lines"} held back: did not match its source.{" "}
          {info.sessionId ? (
            <Link className="text-brand-700 underline" to={`/history/${info.sessionId}`}>
              View in audit
            </Link>
          ) : null}
        </p>
      ) : null}
      {info.previousPackVersion ? (
        <p className="mt-1 text-sm">
          Re-walked on {info.packVersion}; was {info.previousPackVersion}.
        </p>
      ) : null}
      {onRewalk && info.offers.includes("review_findings_and_rewalk") ? (
        <Button className="mt-2" size="sm" variant="outline" disabled={disabled} onClick={onRewalk}>
          Review findings and re-walk
        </Button>
      ) : null}
      <footer className="mt-3 border-t border-neutral-200 pt-2 text-xs text-ink-quiet">
        <p>
          {DISCLAIMER}
          {pack ? ` · Knowledge ${pack}` : ""}
        </p>
        {info.sessionId ? (
          <p>
            ✓ Saved to audit as {info.sessionId} ·{" "}
            <Link className="text-brand-700 underline" to={`/history/${info.sessionId}`}>
              View in history
            </Link>
          </p>
        ) : null}
      </footer>
    </article>
  );
}
