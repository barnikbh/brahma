# Team Allocation — Brahma

A **Bolt** is one build pass over one unit of work that ends in something that runs. A **mob** is the group that builds a Bolt together.

Upstream: `bolt-plan.md` (B1–B8), `unit-of-work.md`, `team-practices.md` (one builder, commit straight to `main`).

Team Formation did not run for this plan (`mvp` scope), so there is one mob for every Bolt: **you, the builder, working with the AI developer (aidlc-developer-agent)**. The AI writes the code and tests; you approve each plan, review each checkpoint, and own the knowledge content and every outside dependency.

| Bolt | Unit | Builds the code | Owns decisions and content |
|---|---|---|---|
| B1 | U1 knowledge graph and content | aidlc-developer-agent | You: IBD content drafted with Claude, checked by your reviewer |
| B2 | U2 platform | aidlc-developer-agent | You: provider keys in your local environment |
| B3 | U3 cases and safety | aidlc-developer-agent | You |
| B4 | U4 grounded agent | aidlc-developer-agent | You |
| B5 | U5 knowledge updates | aidlc-developer-agent | You |
| B6 | U7 benchmark | aidlc-developer-agent | You: expected pathways drafted with Claude; reviewer checks the 16 IBD ones |
| B7 | U8 web app | aidlc-developer-agent | You: visual match to your handover |
| B8 | U6 prescriptions and follow-up | aidlc-developer-agent | You: cut call at Nov 2 noon |

There is one team, so no cross-team board is needed.
