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
