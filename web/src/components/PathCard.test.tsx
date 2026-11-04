import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TraversePath } from "@/api/types";
import { PathCard } from "./PathCard";

const CARD: TraversePath = {
  drug: { nodeId: "IBD-N51", label: "Hydrocortisone 100 mg IV", type: "drug" },
  tier: { nodeId: "IBD-N41", label: "UC Tier 2", type: "treatment_tier" },
  review: [
    { nodeId: "IBD-N80", label: "Day 3: more than 8 stools a day", type: "response_criterion" },
  ],
  monitor: [{ nodeId: "IBD-N70", label: "Stool frequency", type: "monitoring" }],
  watchOuts: [{ nodeId: "IBD-N90", label: "Toxic megacolon", type: "watch_out" }],
  nextTiers: [{ nodeId: "IBD-N42", label: "UC Tier 3", type: "treatment_tier" }],
};

describe("PathCard", () => {
  it("shows the drug, grouped next steps with chips, and the follow-up hint", () => {
    render(<PathCard path={CARD} />);
    expect(screen.getByText(/Now on Hydrocortisone 100 mg IV/)).toBeInTheDocument();
    expect(screen.getByText("Day-3 review")).toBeInTheDocument();
    expect(screen.getByText("Monitor")).toBeInTheDocument();
    expect(screen.getByText("Watch for")).toBeInTheDocument();
    expect(screen.getByText("If UC Tier 2 fails")).toBeInTheDocument();
    for (const id of ["IBD-N51", "IBD-N80", "IBD-N70", "IBD-N90", "IBD-N42"]) {
      expect(document.querySelector(`[data-node-chip="${id}"]`)).toBeInTheDocument();
    }
    expect(screen.getByText(/type the outcome here/)).toBeInTheDocument();
  });

  it("skips empty groups and says so when no tier follows", () => {
    render(<PathCard path={{ ...CARD, review: [], nextTiers: [] }} />);
    expect(screen.queryByText("Day-3 review")).not.toBeInTheDocument();
    expect(screen.getByText("Monitor")).toBeInTheDocument();
    expect(screen.getByText("No further tier in this pack.")).toBeInTheDocument();
  });
});
