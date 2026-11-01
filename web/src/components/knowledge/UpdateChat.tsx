// The knowledge update: a source website and a short note of what should change. The
// assistant reads the page, drafts the node changes and cites the source, asking only what
// the page cannot answer. A reviewer publishes.

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, api } from "@/api/client";
import type { Proposal, UpdateThread } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { formatWhen } from "@/lib/utils";

export interface UpdateChatProps {
  pack: string;
  /** Text to put in the box, e.g. from "Update this node" in Browse. */
  seed?: { text: string; key: number } | null;
  onProposal: (proposal: Proposal) => void;
}

function withScheme(url: string): string {
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

export function UpdateChat({ pack, seed, onProposal }: UpdateChatProps) {
  const [thread, setThread] = useState<UpdateThread | null>(null);
  const [source, setSource] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const end = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .updateThreads()
      .then((r) => {
        // Only a waiting question comes back; a finished update starts the box afresh.
        const last = r.threads.find((t) => t.pack === pack);
        if (!cancelled && last?.status === "open") setThread(last);
      })
      .catch(() => undefined); // a failed restore just starts a fresh conversation
    return () => {
      cancelled = true;
    };
  }, [pack]);

  useEffect(() => {
    if (seed) setText(seed.text);
  }, [seed]);

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "nearest" });
  }, [thread?.messages.length]);

  const asking = thread?.status === "open" && thread.messages.length > 0;
  const url = source.trim();
  const note = text.trim();

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if ((!url && !note) || sending) return;
    setSending(true);
    setError(null);
    const message = url
      ? `${note || "Update the graph from this source."}\n\nSource: ${withScheme(url)}`
      : note;
    try {
      const next = await api.sendUpdate({
        text: message,
        threadId: asking ? thread.threadId : undefined,
        pack,
      });
      setThread(next);
      setSource("");
      setText("");
      const made = next.messages[next.messages.length - 1]?.proposalId;
      const proposal = next.proposals.find((p) => p.proposalId === made);
      if (proposal) onProposal(proposal);
    } catch (e) {
      // The message stays in the box so nothing is lost.
      setError(e instanceof ApiError ? e.message : "The message could not be sent.");
    } finally {
      setSending(false);
    }
  };

  return (
    <section aria-label="Update conversation" className="space-y-3 text-sm">
      <p className="text-ink-quiet">
        Paste a source website and say briefly what should change. Brahma reads the page, works out
        the details, drafts the node and cites the source. Nothing goes live until a reviewer
        approves it.
      </p>
      <form onSubmit={(e) => void send(e)} className="space-y-2">
        <label className="block">
          Source website
          <Input
            value={source}
            inputMode="url"
            maxLength={2048}
            onChange={(e) => setSource(e.target.value)}
            placeholder="https://…"
          />
        </label>
        <label className="block">
          What should change?
          <Textarea
            value={text}
            maxLength={3500}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              asking
                ? "Answer the question below…"
                : "For example: update the ustekinumab induction dose"
            }
          />
        </label>
        {error ? (
          <p role="alert" className="text-result-bad">
            ! {error} Your message is kept.
          </p>
        ) : null}
        <div className="flex items-center gap-2">
          <Button type="submit" disabled={sending || (!url && !note)}>
            {sending ? "Reading the source…" : asking ? "Send" : "Read source and draft"}
          </Button>
          {thread ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setThread(null);
                setError(null);
              }}
            >
              Start over
            </Button>
          ) : null}
        </div>
        {sending ? (
          <p role="status" className="text-ink-quiet">
            Reading the page and drafting the node. This takes about 15 seconds.
          </p>
        ) : null}
      </form>
      {thread && thread.messages.length > 0 ? (
        <div
          role="log"
          aria-live="polite"
          aria-label="Conversation"
          className="max-h-80 space-y-2 overflow-y-auto rounded border border-neutral-200 p-2"
        >
          {thread.messages.map((m) => (
            <div
              key={m.position}
              data-role={m.role}
              className={
                m.role === "doctor"
                  ? "ml-8 rounded bg-brand-50 p-2"
                  : "mr-8 rounded border border-neutral-200 p-2"
              }
            >
              <p className="text-xs text-ink-quiet">
                {m.role === "doctor" ? (thread.profileName ?? "You") : "Brahma"} ·{" "}
                {formatWhen(m.createdAt)}
              </p>
              <p className="whitespace-pre-wrap break-words">{m.text}</p>
            </div>
          ))}
          <div ref={end} />
        </div>
      ) : null}
      {thread?.status === "stuck" ? (
        <p role="status" className="text-result-pending">
          ? This update stopped without a draft. Send a new one with a source that covers it.
        </p>
      ) : null}
    </section>
  );
}
