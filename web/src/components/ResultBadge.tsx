import { Badge, type BadgeProps } from "@/components/ui/badge";

// FR5.7 / NFR3: a result always shows a symbol and a word, never colour alone.
export type ResultKind = "low" | "high" | "abnormal" | "normal" | "not_tested" | "planned";

const LOOK: Record<ResultKind, { symbol: string; word: string; variant: BadgeProps["variant"] }> = {
  low: { symbol: "↓", word: "Low", variant: "bad" },
  high: { symbol: "↑", word: "High", variant: "bad" },
  abnormal: { symbol: "!", word: "Abnormal", variant: "bad" },
  normal: { symbol: "✓", word: "Normal", variant: "ok" },
  not_tested: { symbol: "?", word: "Not yet tested", variant: "pending" },
  planned: { symbol: "◷", word: "Planned", variant: "quiet" },
};

const NORMAL_WORDS = new Set(["negative", "normal", "none", "absent", "not detected"]);

/** The kind for a recorded result value ("negative" is normal, anything else abnormal). */
export function resultKind(value: string | null | undefined): ResultKind {
  const text = (value ?? "").trim().toLowerCase();
  if (!text) return "not_tested";
  if (NORMAL_WORDS.has(text)) return "normal";
  if (text === "low" || text.startsWith("below")) return "low";
  if (text === "high" || text.startsWith("above")) return "high";
  if (text === "planned") return "planned";
  return "abnormal";
}

export function ResultBadge({
  kind,
  value,
  compact = false,
}: {
  kind: ResultKind;
  value?: string | null;
  /** Smaller, single-line badge for map nodes; long details are truncated. */
  compact?: boolean;
}) {
  const look = LOOK[kind];
  const detail = value && value.toLowerCase() !== look.word.toLowerCase() ? value : null;
  return (
    <Badge
      variant={look.variant}
      data-result={kind}
      className={compact ? "max-w-full gap-0.5 px-1.5 py-0 text-[10px] leading-4" : undefined}
    >
      <span aria-hidden="true">{look.symbol}</span>
      <span>{look.word}</span>
      {detail ? (
        <span className={compact ? "truncate font-normal" : "font-normal"}>· {detail}</span>
      ) : null}
    </Badge>
  );
}
