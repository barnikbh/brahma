# Accessibility Checklist — Brahma

Target: WCAG 2.1 AA, checked against the five items in `requirements.md` NFR3 (Q5). Upstream: `wireframes.md` (per-screen accessibility notes), `mockups.md`, `interaction-spec.md`, `design-system-mapping.md` (contrast table), `stories.md` (AC3.5.4).

## The Five Items

| # | Item | How Brahma meets it | How it is checked |
|---|------|--------------------|-------------------|
| 1 | Status never by colour alone | Every result, check and status has a symbol and a word (ResultChip, safety lines, benchmark Pass / Below 95%) | Component tests assert the word is present; review screenshots in greyscale |
| 2 | Text contrast ≥ 4.5:1 | Token pairs in `design-system-mapping.md` all pass | Automated contrast check (axe-core) in the browser smoke test |
| 3 | Targets ≥ 44 × 44 px | Buttons, chips and map nodes (100 × 72 px) meet it; zoom buttons 44 px | Smoke test measures key controls |
| 4 | Fully keyboard operable | Tab order per screen below; map arrow-key navigation; Escape closes the panel; zoom and card toggle are buttons; visible focus ring | Keyboard-only run of the demo walk in the smoke test |
| 5 | Labelled inputs and map nodes | Every input has a visible label; nodes carry `aria-label` "<type>, <label>, <status>, <result>" | axe-core "label" and "button-name" rules pass |

## Per Screen

| Screen | Headings | Landmarks | Keyboard entry point | Live announcements |
|--------|----------|-----------|----------------------|--------------------|
| Sign-in | h1 "Sign in" | header, main, footer | First profile radio | — |
| First run | h1 per step | header, main | First checkbox / Next | — |
| Patients | h1 greeting, h2 per card | header, nav, main | Patient search | Result count (polite) |
| Workspace | h1 case ID (visually the card), h2 chat, h2 map, h3 pathway sections | header, nav, main (two labelled regions), complementary (card, panel) | Chat composer | Brahma's messages and forms (polite); errors (assertive) |
| Node panel | h3 node title | complementary | Panel heading | — |
| Prescription | h2 editor, h2 preview | header, main | First include toggle | Blocked-sign reason (assertive) |
| Follow-up | h2 chat, h2 timeline | header, main, complementary | Results form | Verdict (polite); each chart has a text summary |
| History | h1 "Session history", h2 session | header, nav, main, complementary | Session search | — |
| Knowledge | h2 per panel | header, nav, main | "Node to change" select | Proposal created / failed |
| Benchmark | h1, h2 "Per case" | header, nav, main | Case filter | Run progress (polite) |

## Known Risks

- **React Flow keyboard access** is limited out of the box; arrow-key traversal in walk order and node `aria-label`s are custom work (US3.5).
- **Streaming answers** can flood a screen reader; announcements are per completed section, not per token.
