// Screens 04–13: the consultation workspace. Owns the case view, the walk stream state
// machine, the tab lock and the banners (BR3).

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "@/api/client";
import type { EditOutcome, FormField, MapData, MapEdge, MapNode, NodeDetail } from "@/api/types";
import { Banner } from "@/components/Banner";
import { ChatThread } from "@/components/ChatThread";
import { GraphCanvas } from "@/components/GraphCanvas";
import { NodePanel } from "@/components/NodePanel";
import { PatientCard } from "@/components/PatientCard";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { useSession } from "@/state/session";
import { useCase } from "@/state/useCase";
import { useLock } from "@/state/useLock";
import { retryRequest, viewStatus, type ChatItem } from "@/state/walkReducer";

type LineItem = Extract<ChatItem, { kind: "line" }>;
type FormItem = Extract<ChatItem, { kind: "form" }>;

const EDIT_FIELDS: { name: string; label: string }[] = [
  { name: "drug", label: "Drug" },
  { name: "route", label: "Route" },
  { name: "doseValue", label: "Dose value" },
  { name: "doseUnit", label: "Dose unit" },
  { name: "frequency", label: "Frequency" },
  { name: "duration", label: "Review point" },
];

const MAX_TEXT = 4000;

interface PathContext {
  prefix: string;
  nodeId: string;
  label: string;
}

/** Where an option, planned or chosen node sits, from the map's own edges. */
function contextLineFor(
  selected: MapNode | undefined,
  nodes: MapNode[],
  edges: MapEdge[],
): PathContext | null {
  if (
    !selected ||
    (selected.status !== "option" && selected.status !== "planned" && selected.status !== "chosen")
  ) {
    return null;
  }
  const incoming = edges.find(
    (e) => e.to === selected.nodeId && nodes.some((n) => n.nodeId === e.from),
  );
  if (!incoming) return null;
  const parent = nodes.find((n) => n.nodeId === incoming.from);
  if (!parent) return null;
  let prefix = "During";
  if (selected.status === "option") prefix = "Option of";
  else if (selected.status === "chosen") prefix = "Chosen for";
  else if (selected.type === "treatment_tier") prefix = "Next tier after";
  return { prefix, nodeId: parent.nodeId, label: parent.label };
}

const LIT_STATUSES = new Set(["todo_first", "due", "watch", "present", "now"]);

export function WorkspacePage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { session } = useSession();
  const { view, loadError, state, dispatch, walk, reload, setView } = useCase(caseId);
  const lock = useLock(caseId, view !== null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [highlightNode, setHighlightNode] = useState<string | null>(null);
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [composerError, setComposerError] = useState<string | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [edits, setEdits] = useState<Record<string, EditOutcome>>({});

  useEffect(() => {
    if (lock !== "pending") dispatch({ type: "lock", state: lock });
  }, [lock, dispatch]);

  const status = viewStatus(state);
  const readOnly = state.readOnly;
  const version = state.map.version || view?.pinnedVersion || "";

  const selectedLineIds = useMemo(() => {
    const ids = new Set<string>();
    if (selectedLineId) ids.add(selectedLineId);
    if (highlightNode) {
      for (const item of state.items) {
        if (item.kind === "line" && item.nodeIds.includes(highlightNode)) ids.add(item.id);
      }
    }
    return ids;
  }, [selectedLineId, highlightNode, state.items]);

  const selectLine = useCallback((line: LineItem) => {
    setSelectedLineId(line.id);
    setHighlightNode(null);
    if (line.nodeIds[0]) {
      setSelectedNodeId(line.nodeIds[0]);
      setPanelOpen(true);
    }
  }, []);

  const selectNode = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      setHighlightNode(nodeId);
      setSelectedLineId(null);
      setPanelOpen(true);
      const line = state.items.find((i) => i.kind === "line" && i.nodeIds.includes(nodeId));
      if (line) {
        document
          .querySelector(`[data-line-id="${line.id}"]`)
          ?.scrollIntoView?.({ block: "nearest" });
      }
    },
    [state.items],
  );

  const closePanel = useCallback(() => {
    setPanelOpen(false);
    if (selectedNodeId) {
      document.querySelector<HTMLElement>(`[data-map-node="${selectedNodeId}"]`)?.focus();
    }
  }, [selectedNodeId]);

  const submitForm = (form: FormItem, values: Record<string, unknown>, summary: string) => {
    if (form.formKind === "edit-treatment" && form.nodeId && caseId) {
      void applyEdit(form, values, summary);
      return;
    }
    dispatch({ type: "form_submitted", messageId: form.id, summary });
    void walk({
      mode: "continue",
      walkId: form.walkId ?? state.walkId,
      formMessageId: form.id,
      formValues: values,
    });
  };

  const applyEdit = async (form: FormItem, values: Record<string, unknown>, summary: string) => {
    if (!caseId || !form.nodeId) return;
    if (Object.keys(values).length === 0) {
      dispatch({ type: "edit_done", formId: form.id, summary: null });
      return;
    }
    dispatch({ type: "form_submitted", messageId: form.id, summary });
    try {
      const outcome = await api.treatmentEdit(caseId, form.nodeId, values);
      setEdits((all) => ({ ...all, [form.nodeId!]: outcome }));
      dispatch({ type: "edit_done", formId: form.id, summary });
      dispatch({ type: "notice", text: "Treatment edit applied. Dose and safety re-checked." });
    } catch (e) {
      dispatch({
        type: "request_failed",
        error: {
          code: e instanceof ApiError ? e.code : "edit_failed",
          message: e instanceof ApiError ? e.message : "The edit could not be applied.",
          retryable: false,
        },
      });
    }
  };

  const chooseOption = () => {
    if (!caseId || !selectedNodeId) return;
    void (async () => {
      try {
        const before = new Map(state.map.nodes.map((n) => [n.nodeId, n.status]));
        const result = await api.traverse(caseId, selectedNodeId);
        dispatch({
          type: "traversed",
          map: result.map,
          card: result.path,
          notice: result.notice,
        });
        const lit = result.map.nodes
          .filter((n) => LIT_STATUSES.has(n.status) && before.get(n.nodeId) !== n.status)
          .map((n) => ({ nodeId: n.nodeId, label: n.label, type: n.type }));
        if (lit.length > 0)
          void writeCard(`ch-${Date.now()}`, result.map, lit, "Newly lit by this choice.");
      } catch (e) {
        dispatch({
          type: "request_failed",
          error: {
            code: e instanceof ApiError ? e.code : "traverse_failed",
            message: e instanceof ApiError ? e.message : "The choice could not be recorded.",
            retryable: false,
          },
        });
      }
    })();
  };

  // Record what happened. The map re-lights at once from the pack's edges; the model then
  // writes one cited card about only the newly lit nodes (checked by the grounding guard).
  const writeCard = async (
    id: string,
    map: MapData,
    lit: { nodeId: string; label: string; type: string }[],
    notice: string,
  ) => {
    if (!caseId) return;
    dispatch({ type: "care_event", id, map, lit, notice });
    try {
      const card = await api.careEventCard(
        caseId,
        lit.map((n) => n.nodeId),
      );
      dispatch({ type: "care_card", id, lines: card.lines });
    } catch {
      dispatch({ type: "care_card", id, lines: [] });
    }
  };

  const recordEvent = (kind: "present" | "result" | "done", value?: string) => {
    if (!caseId || !selectedNodeId) return;
    void (async () => {
      try {
        const result = await api.careEvent(caseId, { kind, nodeId: selectedNodeId, value });
        await writeCard(`ev-${Date.now()}`, result.map, result.lit, result.notice);
      } catch (e) {
        dispatch({
          type: "request_failed",
          error: {
            code: e instanceof ApiError ? e.code : "event_failed",
            message: e instanceof ApiError ? e.message : "That could not be recorded.",
            retryable: false,
          },
        });
      }
    })();
  };

  const openEdit = (detail: NodeDetail) => {
    const current = { ...detail.node.fields, ...(edits[detail.node.nodeId]?.edit.newValues ?? {}) };
    const fields: FormField[] = EDIT_FIELDS.map((f) => ({
      name: f.name,
      label: f.label,
      kind: "finding",
      value: current[f.name] == null ? null : String(current[f.name]),
    }));
    dispatch({ type: "open_edit", nodeId: detail.node.nodeId, fields });
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const message = text.trim();
    if (!message || !caseId) return;
    setComposerError(null);
    if (status === "empty" || (status === "error" && !state.walkId)) {
      setText("");
      await walk({ mode: "start", text: message });
      return;
    }
    if (state.done?.followUp && status !== "working") {
      // After a walk has ended, chat text is read as treatment history and answered at
      // once from the graph (no extra button).
      setText("");
      await walk({ mode: "follow_up", text: message });
      return;
    }
    try {
      const result = await api.sendMessage(caseId, message);
      setText("");
      dispatch({ type: "doctor_message", text: message });
      dispatch({
        type: "notice",
        text:
          result.offers.length > 0
            ? "Noted. Use “Review findings and re-walk” when this walk ends."
            : "Noted. Use Re-walk to walk the graph again with the latest findings.",
      });
    } catch (e) {
      setComposerError(e instanceof ApiError ? e.message : "The message could not be sent.");
    }
  };

  if (loadError && !view) {
    return (
      <Banner
        role="alert"
        actions={
          <Button size="sm" variant="outline" onClick={() => void reload()}>
            Retry
          </Button>
        }
      >
        {loadError.message}
      </Banner>
    );
  }
  if (!view) {
    return (
      <p role="status" className="text-sm text-ink-quiet">
        Loading case…
      </p>
    );
  }

  const composerOpen =
    !readOnly &&
    (status === "empty" ||
      status === "answered" ||
      status === "out_of_knowledge" ||
      (status === "needs_data" && state.done !== null) ||
      (status === "error" && !state.walkId));
  const selectedNode = state.map.nodes.find((n) => n.nodeId === selectedNodeId);
  const laneOpen = selectedNodeId ? state.openLanes[selectedNodeId] : undefined;
  const settled = state.done !== null;
  const chooseUnavailable =
    selectedNode?.status === "option" && !settled ? "Available once the walk answers." : null;
  const contextLine = contextLineFor(selectedNode, state.map.nodes, state.map.edges);

  return (
    <div className="space-y-3">
      <PatientCard
        view={view}
        readOnly={readOnly}
        onExit={() => navigate("/patients")}
        onUpdated={(next) => {
          setView(next);
          dispatch({ type: "notice", text: "Patient details updated. Doses are re-read." });
        }}
      />
      {readOnly ? <Banner>This case is open in another tab. This view is read-only.</Banner> : null}
      {view.newerVersion && !bannerDismissed ? (
        <Banner
          actions={
            <>
              <Button
                size="sm"
                disabled={readOnly || status === "working"}
                onClick={() => {
                  setBannerDismissed(true);
                  void walk({ mode: "rewalk" });
                }}
              >
                Re-walk on {view.newerVersion}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setBannerDismissed(true)}>
                Dismiss
              </Button>
            </>
          }
        >
          Newer version {view.newerVersion} available: re-walk? This case used{" "}
          {view.pinnedVersion ?? "an earlier version"}.
        </Banner>
      ) : null}
      <div className="grid grid-cols-[minmax(440px,2fr)_3fr] gap-4">
        <section
          aria-label="Consultation chat"
          className="flex max-h-[calc(100vh-220px)] min-h-[560px] flex-col rounded-card border border-neutral-300 bg-white"
        >
          <header className="flex items-center justify-between border-b border-neutral-200 px-4 py-2">
            <div>
              <p className="font-mono text-xs uppercase text-ink-quiet">
                Case {view.case.caseId} · synthetic
              </p>
              <h2 className="font-semibold">Consultation chat</h2>
            </div>
            <span className="text-xs text-ink-quiet" data-testid="workspace-status">
              {status.replace(/_/g, " ")}
            </span>
          </header>
          <div className="flex-1 overflow-y-auto bg-sage-page/40 p-4">
            <ChatThread
              state={state}
              status={status}
              readOnly={readOnly}
              doctorName={session?.profile.displayName ?? "doctor"}
              selectedLineIds={selectedLineIds}
              onSelectLine={selectLine}
              onSubmitForm={submitForm}
              onCancelForm={(form) =>
                dispatch({ type: "edit_done", formId: form.id, summary: null })
              }
              onRetry={() => {
                const request = retryRequest(state);
                if (request) void walk(request);
              }}
              onRewalk={() => void walk({ mode: "rewalk" })}
              onSuggest={() => navigate("/knowledge")}
              onStopExplore={(laneId) => {
                const branch = Object.entries(state.openLanes).find(([, l]) => l === laneId);
                if (branch && state.walkId) {
                  void walk({
                    mode: "stop_explore",
                    walkId: state.walkId,
                    branchNodeId: branch[0],
                  });
                }
              }}
            />
          </div>
          <form className="border-t border-neutral-200 p-3" onSubmit={(e) => void send(e)}>
            <label htmlFor="composer" className="text-xs font-medium">
              {status === "empty"
                ? "Describe the patient: history, symptoms with duration, results with units"
                : "Message the agent: add case history or new results"}
            </label>
            <div className="mt-1 flex gap-2">
              <Textarea
                id="composer"
                value={text}
                maxLength={MAX_TEXT}
                disabled={!composerOpen}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send(e);
                  }
                }}
                placeholder="e.g. 34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g"
              />
              <Button type="submit" disabled={!composerOpen || !text.trim()}>
                Send
              </Button>
            </div>
            {composerError ? (
              <p role="alert" className="mt-1 text-xs text-result-bad">
                ! {composerError} Your text is kept.
              </p>
            ) : null}
            <p className="mt-1 text-xs text-ink-quiet">
              Decision support, not diagnosis · answers come only from the knowledge graph
            </p>
            {settled && !readOnly ? (
              <Button
                className="mt-1"
                size="sm"
                variant="ghost"
                disabled={status === "working"}
                onClick={() => {
                  setBannerDismissed(true);
                  void walk({ mode: "rewalk" });
                }}
              >
                Re-walk on the latest knowledge base
              </Button>
            ) : null}
          </form>
        </section>
        <div className="relative min-w-0 overflow-x-auto">
          <GraphCanvas
            nodes={state.map.nodes}
            edges={state.map.edges}
            version={version}
            selectedNodeId={selectedNodeId}
            onSelectNode={selectNode}
            timeline={state.map.timeline}
          />
          {panelOpen && selectedNodeId && version ? (
            <NodePanel
              key={selectedNodeId}
              nodeId={selectedNodeId}
              version={version}
              caseId={caseId}
              edit={edits[selectedNodeId] ?? null}
              editorName={session?.profile.displayName}
              readOnly={readOnly}
              canExplore={Boolean(settled && selectedNode && selectedNode.status === "not_taken")}
              exploring={Boolean(laneOpen && laneOpen !== "pending")}
              canChoose={Boolean(settled && selectedNode && selectedNode.status === "option")}
              chooseUnavailable={chooseUnavailable}
              contextLine={contextLine}
              onClose={closePanel}
              onEdit={openEdit}
              onChoose={chooseOption}
              careStatus={selectedNode?.status}
              careReason={selectedNode?.reason}
              onEvent={settled ? recordEvent : undefined}
              onExplore={() => {
                if (state.walkId && selectedNodeId) {
                  void walk({
                    mode: "explore",
                    walkId: state.walkId,
                    branchNodeId: selectedNodeId,
                  });
                }
              }}
              onStopExplore={() => {
                if (state.walkId && selectedNodeId) {
                  void walk({
                    mode: "stop_explore",
                    walkId: state.walkId,
                    branchNodeId: selectedNodeId,
                  });
                }
              }}
              onSuggest={() => navigate(`/knowledge?node=${encodeURIComponent(selectedNodeId)}`)}
              onReview={(reviewNodeId, value) => {
                if (state.walkId) {
                  void walk({
                    mode: "review",
                    walkId: state.walkId,
                    branchNodeId: reviewNodeId,
                    reviewValue: value,
                  });
                }
              }}
              onSelectNode={selectNode}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
