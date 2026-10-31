# Security Design — u8-web-app

Upstream: `security-requirements.md` and `tech-stack-decisions.md` (U8), `functional-spec.md` (U8), `contract-summary.md` (C8).

- **NFR2.2:** In the walk reducer, the only state that holds answer text is `lines`, and only `line` events append to it. Progress messages use a fixed label map; error messages come from the server's `message` field.
- **NFR5.2:** `fetch` is called with `credentials: "same-origin"`. The frontend reads no environment variables at runtime, and the code contains no keys.
- **NFR6.2:** There is no file input except the knowledge source URL. Every patient label is rendered through a `Synthetic` badge component.
- **NFR8.6:** All text is rendered through React text nodes, and `dangerouslySetInnerHTML` is never used. An ESLint rule enforces this.
- **NFR3.1:**
  - shadcn/ui components are built on Radix, which provides keyboard support and labels.
  - A focus ring comes from the design tokens.
  - Status is shown with a symbol and a word as well as colour (`ResultBadge`).
  - Contrast follows the checks in `design-system-mapping.md`.
- **FR15.1:** `AppShell` renders the disclaimer and the pack chips on every page.
