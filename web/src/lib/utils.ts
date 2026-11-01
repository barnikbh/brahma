import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind class names (shadcn/ui convention). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** "IBD 1.0; URO 0.1" or ["IBD 1.0"] as chip labels "IBD v1.0". */
export function packChips(versions: string | string[]): string[] {
  const list = Array.isArray(versions) ? versions : versions.split(";");
  return list
    .map((v) => v.trim())
    .filter(Boolean)
    .map((v) => {
      const [pack, number] = v.split(/[ @-]/);
      return number ? `${pack} v${number}` : v;
    });
}

/** Split "a, b ,c" into trimmed non-empty items. */
export function splitList(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/** A short local date-time for lists. */
export function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Weight bands as readable lines, e.g. "≤55 kg: 260 mg", ">55 to 85 kg: 390 mg". */
export function formatDoseBands(bands: unknown): string[] {
  if (!Array.isArray(bands)) return [];
  return bands.map((band: Record<string, unknown>) => {
    const { weightMinKg: low, weightMaxKg: high, doseValue, doseUnit } = band;
    const dose = `${String(doseValue)} ${String(doseUnit)}`;
    if (low === null || low === undefined) return `≤${String(high)} kg: ${dose}`;
    if (high === null || high === undefined) return `>${String(low)} kg: ${dose}`;
    return `>${String(low)} to ${String(high)} kg: ${dose}`;
  });
}

export interface DiffPart {
  kind: "same" | "removed" | "added";
  text: string;
}

/** A word-level diff of two texts (longest common subsequence), spaces kept with the words. */
export function wordDiff(before: string, after: string): DiffPart[] {
  const a = before.split(/(?<=\s)/);
  const b = after.split(/(?<=\s)/);
  const lengths = Array.from({ length: a.length + 1 }, () =>
    new Array<number>(b.length + 1).fill(0),
  );
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lengths[i][j] =
        a[i] === b[j] ? lengths[i + 1][j + 1] + 1 : Math.max(lengths[i + 1][j], lengths[i][j + 1]);
    }
  }
  const parts: DiffPart[] = [];
  const push = (kind: DiffPart["kind"], text: string) => {
    const last = parts[parts.length - 1];
    if (last?.kind === kind) last.text += text;
    else parts.push({ kind, text });
  };
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      push("same", a[i]);
      i++;
      j++;
    } else if (j >= b.length || (i < a.length && lengths[i + 1][j] >= lengths[i][j + 1])) {
      push("removed", a[i++]);
    } else {
      push("added", b[j++]);
    }
  }
  return parts;
}
