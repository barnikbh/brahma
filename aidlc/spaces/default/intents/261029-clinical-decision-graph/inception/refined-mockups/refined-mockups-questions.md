# Refined Mockups — Questions

Context: your Brahma design handover (`docs/design-handover/`) already gives high-fidelity screens, tokens, states and accessibility rules, and the approved `wireframes.md`, `user-flow.md`, `stories.md` and `requirements.md` settle the rest. Per your project rule to keep process detail light and pick sensible defaults instead of asking (`project.md`, Corrections), each answer below is taken from those sources or is a lightweight default, and the summary at the end is your one check.

## Q1. [Design] How each story appears in the UI

A. Each story maps to the handover screen that already shows it (for example US3.2 → screen 08), and new detail from the requirements is added as annotations on that screen
B. Redraw every screen from scratch
C. Only the Must stories get mockups
D. Not yet defined
X. Other (please specify)

[Answer]: A (from your handover: 26 screens and states already cover every story; requirement changes since then, such as the claim check, safety "Not checked" and version banner, are added as annotations)

## Q2. [Design] Interaction patterns

A. Chat-first: structured input as forms inside the chat; detail in a side panel over the map; no modal dialogs except Void reason and sign-out
B. Modal dialogs for every form
C. A step-by-step wizard for the walk
D. Not yet defined
X. Other (please specify)

[Answer]: A (from your handover: Chat-first interaction, Treatment details and editing)

## Q3. [Design] States each screen handles

A. Every screen lists loading, empty, error and success, plus its own states (the workspace's nine; the version banner; "Not checked"; read-only second tab)
B. Workspace states only
C. Happy path only
D. Not yet defined
X. Other (please specify)

[Answer]: A (from requirements.md FR5.6, FR1.7, FR7.3, NFR7, and the earlier review's point on empty and error states)

## Q4. [Design] Design system and component library

A. Your handover tokens (indigo + sage, result colours, Georgia + Inter) as design tokens, on React with Tailwind CSS and shadcn/ui components, and React Flow for the network map
B. A different component library
C. Hand-built components only
D. Not yet defined
X. Other (please specify)

[Answer]: A (tokens from your handover; the library choice is a lightweight default per your project rule, chosen because it fits React and TypeScript strict and needs no design work of its own)

## Q5. [Design] Accessibility level

A. WCAG 2.1 AA, checked against the five-item list in requirements.md NFR3
B. WCAG 2.1 AAA
C. No formal level
D. Not yet defined
X. Other (please specify)

[Answer]: A (from requirements.md NFR3; rough-mockups Q6)

## Q6. [Design] Responsive breakpoints

A. Desktop and laptop only: designed at 1440 px, working down to 1280 px; below 1280 px the map panel narrows and scrolls rather than reflowing
B. Desktop plus tablet
C. Fully responsive to phone
D. Not yet defined
X. Other (please specify)

[Answer]: A (from requirements.md NFR4; rough-mockups Q6)

## Consolidated Summary Confirmation

- Your handover screens are the high-fidelity mockups; each story maps to its screen, and changes from the requirements since (claim check, safety "Not checked", version banner, read-only second tab, input checks) are added as annotations (Q1)
- Chat-first interactions: input as forms inside the chat, detail in a side panel over the map; modal dialogs only for the Void reason and sign-out (Q2)
- Every screen lists loading, empty, error and success states plus its own; the workspace keeps its nine states (Q3)
- Design system: your handover tokens (indigo + sage, result colours, Georgia + Inter) on React with Tailwind CSS and shadcn/ui, and React Flow for the network map; the library is a lightweight default I chose (Q4)
- Accessibility: WCAG 2.1 AA, checked against the five-item list in the requirements (Q5)
- Desktop and laptop only, 1280 to 1440 px; no tablet or phone layouts (Q6)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
