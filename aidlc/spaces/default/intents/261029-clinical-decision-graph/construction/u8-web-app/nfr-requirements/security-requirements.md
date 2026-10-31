# Security Requirements — u8-web-app

Upstream: `functional-spec.md` (U8), `requirements.md` (NFR2, NFR3, NFR5, NFR6, FR15), `contract-summary.md` (C8).

- **NFR2.2** Answer text is only ever rendered from `line` events. Model text is never shown in progress or error messages (BR3.2).
- **NFR5.2** The frontend holds no secrets. It talks only to the same-origin `/api`, and uses the session cookie set by the server.
- **NFR6.2** No upload or import of patient records. All patient labels say "synthetic" (FR15.2).
- **NFR8.6** Server and node text is rendered as text, never as HTML, so it can't inject markup (XSS).
- **NFR3.1** The five accessibility items in `accessibility-checklist.md` apply (keyboard, contrast, labels, focus, not colour alone).
- **FR15.1** The disclaimer appears on every screen.
