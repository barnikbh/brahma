import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Sage information banner (shadcn/ui Alert, sage variant). Never a warning colour. */
export function Banner({
  children,
  actions,
  className,
  role = "status",
}: {
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  role?: "status" | "alert";
}) {
  return (
    <div
      role={role}
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 rounded-card border border-sage-line bg-sage-note px-4 py-2 text-sm text-sage-ink",
        className,
      )}
    >
      <div>{children}</div>
      {actions ? <div className="flex gap-2">{actions}</div> : null}
    </div>
  );
}
