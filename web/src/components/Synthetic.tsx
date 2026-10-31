import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";

/** Every patient name and case ID carries the word "synthetic" (FR15.2, NFR6.2). */
export function Synthetic({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span>{children}</span>
      <Badge variant="quiet" className="font-mono text-[10px] uppercase tracking-wide">
        synthetic
      </Badge>
    </span>
  );
}
