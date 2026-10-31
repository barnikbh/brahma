# Performance Design — u8-web-app

Upstream: `performance-requirements.md` and `tech-stack-decisions.md` (U8), `functional-spec.md` (U8), `contract-summary.md` (C8).

- **NFR1.5:** `walkStream.ts` decodes the stream in chunks and passes each event to a reducer straight away. Events are applied as they arrive, with no batching.
- **NFR1.6:** Node positions in React Flow are computed once per walk, column by column. Light-up only changes a node's status class, so nodes don't re-render.
- **NFR4.4:** Vite builds for the targets `chrome>=120, firefox>=120, safari>=17`. A CSS media query shows the desktop-only notice below 1280 px.
