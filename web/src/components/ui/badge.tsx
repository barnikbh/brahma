import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "border-neutral-300 bg-white text-ink",
        brand: "border-brand-700 bg-white text-brand-700",
        sage: "border-sage-line bg-sage-note text-sage-ink",
        bad: "border-result-bad bg-red-50 text-result-bad",
        ok: "border-result-ok bg-green-50 text-result-ok",
        pending: "border-dashed border-result-pending bg-amber-50 text-result-pending",
        quiet: "border-neutral-300 bg-neutral-50 text-ink-quiet",
        explore: "border-dashed border-explore bg-fuchsia-50 text-explore",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
