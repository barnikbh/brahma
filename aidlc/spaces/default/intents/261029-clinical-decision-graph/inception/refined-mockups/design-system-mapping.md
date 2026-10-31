# Design System Mapping — Brahma

Upstream: your handover (`docs/design-handover/Brahma - Design Handover.md`, Brand: name and colour), `mockups.md`, `interaction-spec.md`, `requirements.md` (NFR3, NFR12), `team-practices.md` (TypeScript strict, ESLint, Prettier). Answers: Q4.

**Stack (Q4):** React + TypeScript, Tailwind CSS for tokens and layout, shadcn/ui for base components, React Flow for the network map. This is a lightweight default chosen per your project rule; it adds no design work of its own and keeps every component themable from the handover tokens.

## Tokens

| Token | Hex | Tailwind name | Use (from handover) |
|---|---|---|---|
| Indigo 900 | #312E81 | `brand-900` | Wordmark, primary buttons, active nav, agent avatar, signed stamp |
| Indigo 700 | #4338CA | `brand-700` | Walked path, selection, citation chips, links |
| Indigo 200 | #C7D2FE | `brand-200` | Selection halo |
| Indigo 50 | #EEF2FF | `brand-50` | Used-node fill, completed steps |
| Sage page | #F1F4F0 | `sage-page` | Page background |
| Sage note bg / border / text | #E6EEE4 / #BFCDBB / #2F4034 | `sage-note`, `sage-line`, `sage-ink` | Disclaimer and information banners |
| Ink | #171717 | `ink` | Body text |
| Quiet | #525252 | `ink-quiet` | Secondary text, planned monitoring |
| Fuchsia 700 | #A21CAF | `explore` | Exploring a side branch only |
| Result red | #B91C1C | `result-bad` | Out of range, abnormal, allergy conflict |
| Result green | #15803D | `result-ok` | Normal, signed checks passed |
| Result amber | #B45309 | `result-pending` | Test needed, not checked |

**Rules carried from the handover:** brand indigo never stands for a result; red, green and amber are only for results and status; fuchsia only for exploring.

**Type:** Georgia (serif) for the wordmark and screen headings; Inter for everything else; base 14 px, line height 1.5.

**Spacing and shape:** 4 px grid; cards 8 px radius, 1 px border; focus ring 2 px `brand-700` with 2 px offset.

## Components

| Brahma component | Built from | Notes |
|---|---|---|
| Top nav, buttons, inputs, select, checkbox | shadcn/ui Button, Input, Select, Checkbox | Themed with tokens above |
| ChatForm | shadcn/ui Form + Badge (chips) | Dark 2 px outline when open |
| PathwayAnswer | Custom on shadcn/ui Card | Node chips are Badge with `brand-700` outline |
| NetworkMap | React Flow custom node (100 × 72 px) and edge types | Fixed column layout computed, not auto-laid out |
| NodeDetailPanel | shadcn/ui Sheet (non-modal) | Opens from the right over the map |
| PatientCard | Custom, sticky | Collapsible via shadcn/ui Collapsible |
| Banners | shadcn/ui Alert, sage variant | |
| ResultChip | Custom Badge variants | Symbol + word + colour |
| Void dialog, sign-out | shadcn/ui Dialog | The only modals |
| Trend charts (follow-up) | Recharts line chart with a reference band | Could, cut first with FR8 |
| Benchmark bars | Plain CSS bars | No chart library needed |

## Contrast Checks (NFR3, item 2)

| Pair | Ratio | Passes 4.5:1 |
|---|---|---|
| Ink #171717 on Sage page #F1F4F0 | 16.2:1 | Yes |
| Quiet #525252 on white | 7.8:1 | Yes |
| White on Indigo 900 #312E81 | 11.4:1 | Yes |
| Indigo 700 #4338CA on white | 7.9:1 | Yes |
| Result red #B91C1C on white | 6.5:1 | Yes |
| Result green #15803D on white | 5.0:1 | Yes |
| Result amber #B45309 on white | 5.0:1 | Yes |
| Sage ink #2F4034 on Sage note #E6EEE4 | 9.3:1 | Yes |

Computed with the WCAG relative-luminance formula against white or the stated background. Chips on tinted backgrounds are re-checked by the automated contrast test in the build.
