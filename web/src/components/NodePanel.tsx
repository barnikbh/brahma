// Node detail side panel (BR4, A3): node content, dose with formula, safety lines with a
// symbol and words, sources, version, comments, and the Edit / Explore / Suggest actions.

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, api } from "@/api/client";
import type { EditOutcome, NodeDetail, SafetyResult } from "@/api/types";
import { NodeChip } from "@/components/NodeChip";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDoseBands, formatWhen } from "@/lib/utils";

const CHECK_LABEL: Record<SafetyResult["check"], string> = {
  allergy: "Allergy",
  pregnancy: "Pregnancy",
  interaction: "Interactions",
  duplicate_class: "Duplicate class",
};

export function SafetyLine({ result }: { result: SafetyResult }) {
  // "No conflict" is only shown when a node supports it (BR4.2); otherwise Not checked.
  if (result.status === "conflict") {
    return (
      <li className="text-result-bad" data-safety="conflict">
        <span aria-hidden="true">! </span>
        <strong>
          {result.check === "allergy"
            ? "Allergy conflict"
            : `${CHECK_LABEL[result.check]} conflict`}
        </strong>
        : {result.message}{" "}
        {result.nodeIds.map((id) => (
          <NodeChip key={id} nodeId={id} />
        ))}
      </li>
    );
  }
  if (result.status === "ok" && result.nodeIds.length > 0) {
    return (
      <li className="text-result-ok" data-safety="ok">
        <span aria-hidden="true">✓ </span>
        <strong>{CHECK_LABEL[result.check]}</strong>: {result.message}{" "}
        {result.nodeIds.map((id) => (
          <NodeChip key={id} nodeId={id} />
        ))}
      </li>
    );
  }
  return (
    <li className="text-result-pending" data-safety="not_checked">
      <span aria-hidden="true">? </span>
      <strong>{CHECK_LABEL[result.check]}</strong>: Not checked: no grounded safety data
    </li>
  );
}

function text(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

const COMPARATOR_WORD: Record<string, string> = {
  gt: "above",
  ge: "at or above",
  lt: "below",
  le: "at or below",
  eq: "equal to",
};

export interface NodePanelProps {
  nodeId: string;
  version: string;
  caseId?: string;
  edit?: EditOutcome | null;
  editorName?: string;
  readOnly?: boolean;
  canExplore?: boolean;
  exploring?: boolean;
  canChoose?: boolean;
  chooseUnavailable?: string | null;
  contextLine?: { prefix: string; nodeId: string; label: string } | null;
  onClose: () => void;
  onEdit?: (detail: NodeDetail) => void;
  onChoose?: () => void;
  onExplore?: () => void;
  onStopExplore?: () => void;
  onSuggest?: () => void;
  onReview?: (nodeId: string, value: string) => void;
  /** The node's care-loop status and why it is lit, from the map. */
  careStatus?: string;
  careReason?: string | null;
  /** Records an event for this node: a sign present, a result in, or a step done. */
  onEvent?: (kind: "present" | "result" | "done", value?: string) => void;
  onSelectNode?: (nodeId: string) => void;
}

const OBSERVATION_TYPES = new Set(["symptom", "metric", "watch_out", "interaction"]);
const ACTION_TYPES = new Set(["drug", "treatment_tier", "diet"]);

/** The buttons that record what happened. Clicking a block only opens this panel; these
 *  buttons are what change the case, and the map lights the next step from the result. */
function CareActions(props: {
  type: string;
  status?: string;
  reason?: string | null;
  options: string[];
  unit: string | null;
  disabled: boolean;
  value: string;
  onValue: (value: string) => void;
  onEvent: (kind: "present" | "result" | "done", value?: string) => void;
}) {
  const { type, status } = props;
  const isTest = type === "test";
  const isMeasure = type === "monitoring";
  const isSign = OBSERVATION_TYPES.has(type);
  const isStep = ACTION_TYPES.has(type);
  if (!isTest && !isMeasure && !isSign && !isStep) return null;
  const canMark = isStep && (status === "chosen" || status === "entry" || status === "now");
  if (isStep && !canMark && status !== "done") return null;
  return (
    <section aria-label="Record" data-testid="node-care" className="space-y-2">
      {props.reason ? <p className="text-xs font-medium">{props.reason}</p> : null}
      {isSign ? (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={props.disabled || status === "present"}
            onClick={() => props.onEvent("present")}
          >
            Patient has this now
          </Button>
          {status === "present" ? <span className="text-xs text-ink-quiet">Recorded</span> : null}
        </div>
      ) : null}
      {isTest ? (
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (props.value) props.onEvent("result", props.value);
          }}
        >
          <select
            aria-label="Result"
            value={props.value}
            disabled={props.disabled}
            onChange={(e) => props.onValue(e.target.value)}
            className="h-8 rounded border border-neutral-300 bg-white px-2 text-sm"
          >
            <option value="">Result…</option>
            {props.options.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          <Button size="sm" type="submit" disabled={props.disabled || !props.value}>
            Record result
          </Button>
        </form>
      ) : null}
      {isMeasure ? (
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (props.value.trim()) props.onEvent("result", props.value.trim());
          }}
        >
          <Input
            aria-label="Result"
            value={props.value}
            inputMode="decimal"
            disabled={props.disabled}
            onChange={(e) => props.onValue(e.target.value)}
            placeholder={props.unit ? `Value (${props.unit})` : "Value"}
            className="w-32"
          />
          <Button size="sm" type="submit" disabled={props.disabled || !props.value.trim()}>
            Record result
          </Button>
        </form>
      ) : null}
      {canMark ? (
        <Button
          size="sm"
          variant="outline"
          disabled={props.disabled}
          onClick={() => props.onEvent("done")}
        >
          Mark done
        </Button>
      ) : null}
    </section>
  );
}

export function NodePanel(props: NodePanelProps) {
  const { nodeId, version, caseId } = props;
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [commentError, setCommentError] = useState<string | null>(null);
  const [reviewValue, setReviewValue] = useState("");
  const [resultValue, setResultValue] = useState("");
  const heading = useRef<HTMLHeadingElement | null>(null);

  const load = useCallback(async () => {
    setDetail(null);
    setError(null);
    try {
      setDetail(await api.node(version, nodeId, caseId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load this node");
    }
  }, [version, nodeId, caseId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Focus once on open (the panel remounts per node). Never refocus when detail
  // arrives late: the doctor may have moved to the composer, and yanking focus
  // back breaks Enter-to-send there.
  useEffect(() => {
    heading.current?.focus();
  }, []);

  const { onClose } = props;
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const addComment = async (event: FormEvent) => {
    event.preventDefault();
    if (!comment.trim() || !detail) return;
    setCommentError(null);
    try {
      const stored = await api.addComment(version, nodeId, comment.trim());
      setDetail({ ...detail, comments: [stored, ...detail.comments] });
      setComment("");
    } catch (e) {
      setCommentError(e instanceof ApiError ? e.message : "The comment could not be saved.");
    }
  };

  const recordReview = (event: FormEvent) => {
    event.preventDefault();
    if (!reviewValue.trim() || !detail || !caseId) return;
    props.onReview?.(nodeId, reviewValue.trim());
  };

  const edit = props.edit ?? null;
  // The in-memory outcome wins when present; otherwise the stored edit from the
  // detail keeps the marker across reloads (dose/safety already reflect it).
  const edited = edit?.edit ?? detail?.edited ?? null;
  const fields = { ...(detail?.node.fields ?? {}), ...(edited?.newValues ?? {}) };
  const editedKeys = new Set(
    Object.keys(edited?.newValues ?? {}).filter(
      (k) => text(edited?.newValues[k]) !== text(edited?.original[k]),
    ),
  );
  const dose = edit ? edit.dose : detail?.dose;
  const safety = edit ? edit.safety : (detail?.safety ?? []);
  const isDrug = detail?.node.type === "drug";
  const Edited = ({ name }: { name: string }) =>
    editedKeys.has(name) ? <span className="ml-1 text-xs text-brand-700">✎ edited</span> : null;

  return (
    <aside
      role="complementary"
      aria-labelledby="node-panel-title"
      className="absolute inset-y-0 right-0 z-10 w-[380px] overflow-y-auto border-l border-neutral-300 bg-white p-4 shadow-lg"
      data-testid="node-panel"
    >
      <div className="flex items-start justify-between gap-2">
        <h3
          id="node-panel-title"
          ref={heading}
          tabIndex={-1}
          className="font-serif text-lg text-brand-900 focus:outline-none"
        >
          {detail ? detail.node.label : nodeId}
        </h3>
        <Button size="sm" variant="ghost" aria-label="Close node detail" onClick={props.onClose}>
          ✕
        </Button>
      </div>
      {!detail && !error ? (
        <p role="status" className="mt-4 text-sm text-ink-quiet">
          Loading node…
        </p>
      ) : null}
      {error ? (
        <div role="alert" className="mt-4 text-sm">
          <p>Couldn&apos;t load this node. {error}</p>
          <Button className="mt-2" size="sm" variant="outline" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      ) : null}
      {detail ? (
        <div className="mt-2 space-y-4 text-sm">
          <div className="flex flex-wrap gap-2">
            <Badge variant="quiet" className="uppercase">
              {detail.node.type}
            </Badge>
            <NodeChip nodeId={detail.node.nodeId} />
            <Badge variant="sage">From pack {detail.packVersion ?? version}</Badge>
          </div>
          {props.contextLine ? (
            <p className="text-xs text-ink-quiet" data-testid="node-context">
              {props.contextLine.prefix}{" "}
              <strong className="font-semibold">{props.contextLine.label}</strong>{" "}
              <NodeChip nodeId={props.contextLine.nodeId} />
            </p>
          ) : null}
          {detail.leadsTo.length > 0 ? (
            <p className="text-xs" data-testid="node-leads-to">
              If met →{" "}
              {detail.leadsTo.map((target, i) => (
                <span key={target.nodeId}>
                  {i > 0 ? " · " : null}
                  <strong className="font-semibold">{target.label}</strong>{" "}
                  <NodeChip nodeId={target.nodeId} />
                </span>
              ))}
            </p>
          ) : null}
          {detail.nextPaths.length > 0 ? (
            <section aria-label="Where it leads" data-testid="node-next-paths">
              <h4 className="font-semibold">Where it leads</h4>
              <ul className="mt-1 space-y-1">
                {detail.nextPaths.map((target) => (
                  <li key={target.nodeId}>
                    <Button
                      size="sm"
                      variant="link"
                      className="h-auto p-0 text-left text-sm"
                      onClick={() => props.onSelectNode?.(target.nodeId)}
                    >
                      {target.label}
                    </Button>{" "}
                    <NodeChip nodeId={target.nodeId} />
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          {detail.node.type === "response_criterion" &&
          detail.leadsTo.length > 0 &&
          caseId &&
          props.onReview ? (
            <section aria-label="Record review result" data-testid="node-review">
              <h4 className="font-semibold">Record day-3 result</h4>
              {typeof fields.threshold === "number" ? (
                <p className="text-xs text-ink-quiet">
                  Meets when {text(fields.measure)} is{" "}
                  {COMPARATOR_WORD[String(fields.comparator)] ?? String(fields.comparator)}{" "}
                  {fields.threshold}
                  {fields.unit ? ` ${fields.unit}` : ""}
                </p>
              ) : null}
              <form className="mt-1 flex gap-2" onSubmit={recordReview}>
                <Input
                  aria-label="Day-3 result"
                  value={reviewValue}
                  inputMode="decimal"
                  disabled={props.readOnly}
                  onChange={(e) => setReviewValue(e.target.value)}
                  placeholder="e.g. 60"
                />
                <Button type="submit" size="sm" disabled={!reviewValue.trim() || props.readOnly}>
                  Record
                </Button>
              </form>
              <p className="text-xs text-ink-quiet">
                A met criterion opens the next tier as a new review walk.
              </p>
            </section>
          ) : null}
          {caseId && props.onEvent ? (
            <CareActions
              type={detail.node.type}
              status={props.careStatus}
              reason={props.careReason}
              options={
                Array.isArray(fields.resultOptions) ? (fields.resultOptions as string[]) : []
              }
              unit={typeof fields.unit === "string" ? fields.unit : null}
              disabled={Boolean(props.readOnly)}
              value={resultValue}
              onValue={setResultValue}
              onEvent={props.onEvent}
            />
          ) : null}
          <p className="text-xs text-ink-quiet" data-testid="node-updated">
            {detail.updated
              ? `Updated by ${detail.updated.updatedByName} · ${formatWhen(detail.updated.updatedAt)}`
              : `Initial pack v${detail.initialVersion ?? "1.0"}`}
          </p>
          {edited ? (
            <p className="text-brand-700">
              ✎ Edited by {props.editorName ?? edited.editorProfileId}
            </p>
          ) : null}
          <p>{detail.node.content}</p>
          {isDrug ? (
            <dl className="grid grid-cols-[110px_1fr] gap-x-2 gap-y-1">
              <dt className="text-ink-quiet">Drug</dt>
              <dd>
                {text(fields.drug)}
                <Edited name="drug" />
              </dd>
              <dt className="text-ink-quiet">Route</dt>
              <dd>
                {text(fields.route)}
                <Edited name="route" />
              </dd>
              {fields.inductionDoseValue != null ? (
                <>
                  <dt className="text-ink-quiet">Induction dose</dt>
                  <dd data-testid="induction-dose">
                    {text(fields.inductionDoseValue)} {text(fields.inductionDoseUnit)}
                  </dd>
                </>
              ) : null}
              <dt className="text-ink-quiet">
                {fields.inductionDoseValue != null ? "Maintenance dose" : "Pack dose"}
              </dt>
              <dd>
                {fields.doseBasis === "weight_band" ? (
                  formatDoseBands(fields.doseBands).join("; ")
                ) : (
                  <>
                    {text(fields.doseValue)} {text(fields.doseUnit)}
                    {fields.doseBasis === "per_kg" ? " per kg" : ""}
                  </>
                )}
                <Edited name="doseValue" />
              </dd>
              <dt className="text-ink-quiet">This patient</dt>
              <dd data-testid="dose">
                {dose && "value" in dose ? (
                  <>
                    <strong>
                      {dose.value} {dose.unit}
                    </strong>
                    <span className="block text-xs text-ink-quiet">{dose.formula}</span>
                  </>
                ) : dose && "missing" in dose ? (
                  <span className="text-result-pending">? {dose.missing}</span>
                ) : dose && "message" in dose ? (
                  <span className="text-result-pending">? {dose.message}</span>
                ) : (
                  "—"
                )}
              </dd>
              <dt className="text-ink-quiet">Frequency</dt>
              <dd>
                {text(fields.frequency)}
                <Edited name="frequency" />
              </dd>
              <dt className="text-ink-quiet">Review point</dt>
              <dd>
                {text(fields.duration)}
                <Edited name="duration" />
              </dd>
            </dl>
          ) : null}
          {typeof detail.node.fields.entryCriteria === "string" ? (
            <p>
              <span className="text-ink-quiet">Entry criteria: </span>
              {detail.node.fields.entryCriteria}
            </p>
          ) : null}
          {isDrug ? (
            <section aria-label="Safety">
              <h4 className="font-semibold">Safety</h4>
              <ul className="mt-1 space-y-1">
                {safety.length > 0 ? (
                  safety.map((s, i) => <SafetyLine key={`${s.check}-${i}`} result={s} />)
                ) : (
                  <li className="text-result-pending" data-safety="not_checked">
                    <span aria-hidden="true">? </span>Not checked: no grounded safety data
                  </li>
                )}
              </ul>
            </section>
          ) : null}
          <section aria-label="Sources">
            <h4 className="font-semibold">Sources</h4>
            <ul className="mt-1 space-y-1">
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
          <div className="flex flex-wrap gap-2">
            {isDrug && caseId && props.onEdit ? (
              <Button
                size="sm"
                variant="outline"
                disabled={props.readOnly}
                onClick={() => props.onEdit?.(detail)}
              >
                Edit treatment
              </Button>
            ) : null}
            {props.canChoose && props.onChoose ? (
              <Button
                size="sm"
                variant="outline"
                disabled={props.readOnly}
                onClick={props.onChoose}
              >
                Choose this option
              </Button>
            ) : props.chooseUnavailable ? (
              <span>
                <Button size="sm" variant="outline" disabled={true}>
                  Choose this option
                </Button>
                <span className="ml-2 text-xs text-ink-quiet">{props.chooseUnavailable}</span>
              </span>
            ) : null}
            {props.exploring && props.onStopExplore ? (
              <Button
                size="sm"
                variant="outline"
                disabled={props.readOnly}
                onClick={props.onStopExplore}
              >
                Stop exploring
              </Button>
            ) : props.canExplore && props.onExplore ? (
              <Button
                size="sm"
                variant="outline"
                disabled={props.readOnly}
                onClick={props.onExplore}
              >
                Explore this branch
              </Button>
            ) : null}
            {props.onSuggest ? (
              <Button size="sm" variant="ghost" onClick={props.onSuggest}>
                Suggest a change
              </Button>
            ) : null}
          </div>
          <section aria-label="Comments">
            <h4 className="font-semibold">Comments</h4>
            <form className="mt-1 flex gap-2" onSubmit={(e) => void addComment(e)}>
              <Input
                aria-label="Add a comment"
                value={comment}
                maxLength={2000}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment"
              />
              <Button type="submit" size="sm" disabled={!comment.trim()}>
                Add
              </Button>
            </form>
            {commentError ? <p className="text-xs text-result-bad">! {commentError}</p> : null}
            <ul className="mt-2 space-y-1">
              {detail.comments.map((c) => (
                <li key={c.commentId} className="text-xs">
                  <span className="text-ink-quiet">{c.authorProfileId}: </span>
                  {c.text}
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}
    </aside>
  );
}
