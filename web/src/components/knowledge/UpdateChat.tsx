// The update conversation: one free-text box for what to change and the source URLs. The
// assistant drafts node by node, or asks short follow-up questions. A reviewer publishes.

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, api } from "@/api/client";
import type { Proposal, UpdateThread } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { formatWhen } from "@/lib/utils";

export interface UpdateChatProps {
  pack: string;
  /** Text to put in the box, e.g. from "Update this node" in Browse. */
  seed?: { text: string; key: number } | null;
  onProposal: (proposal: Proposal) => void;
}

export function UpdateChat({ pack, seed, onProposal }: UpdateChatProps) {
  const [thread, setThread] = useState<UpdateThread | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const end = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .updateThreads()
      .then((r) => {
        const last = r.threads.find((t) => t.pack === pack);
        if (!cancelled && last) setThread(last);
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

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    setError(null);
    try {
      const next = await api.sendUpdate({ text: text.trim(), threadId: thread?.threadId, pack });
      setThread(next);
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

  const closed = thread?.status === "stuck";
  return (
    <section aria-label="Update conversation" className="space-y-3 text-sm">
      <p className="text-ink-quiet">
        Say what to update in your own words and paste the source URL(s), for example “Update the
        ustekinumab maintenance dose from https://…”. The assistant drafts each node from the page
        and asks if anything is unclear. Nothing goes live until a reviewer publishes it.
      </p>
      <div
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="max-h-80 space-y-2 overflow-y-auto rounded border border-neutral-200 p-2"
      >
        {!thread || thread.messages.length === 0 ? (
          <p className="text-ink-quiet">No messages yet.</p>
        ) : null}
        {thread?.messages.map((m) => (
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
              {m.role === "doctor" ? (thread.profileName ?? "You") : "Assistant"} ·{" "}
              {formatWhen(m.createdAt)}
            </p>
            <p className="whitespace-pre-wrap">{m.text}</p>
          </div>
        ))}
        <div ref={end} />
      </div>
      {closed ? (
        <p role="status" className="text-result-pending">
          ? This conversation ended without a draft. Start a new one.
        </p>
      ) : null}
      <form onSubmit={(e) => void send(e)} className="space-y-2">
        <label className="block">
          Your message
          <Textarea
            value={text}
            maxLength={4000}
            disabled={closed}
            onChange={(e) => setText(e.target.value)}
            placeholder="Update ustekinumab maintenance dose from https://…"
          />
        </label>
        {error ? (
          <p role="alert" className="text-result-bad">
            ! {error} Your message is kept.
          </p>
        ) : null}
        <div className="flex gap-2">
          <Button type="submit" disabled={sending || closed || !text.trim()}>
            {sending ? "Working…" : "Send"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setThread(null);
              setError(null);
            }}
          >
            New conversation
          </Button>
        </div>
      </form>
    </section>
  );
}
