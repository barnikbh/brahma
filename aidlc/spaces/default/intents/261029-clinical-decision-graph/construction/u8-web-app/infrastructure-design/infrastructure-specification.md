# Infrastructure Specification — u8-web-app

Upstream: `performance-design.md`, `security-design.md` and `logical-components.md` (U8), `components.md` (DoctorWebApp), `functional-spec.md` (U8), `contract-summary.md` (C8).

This runs locally only. There is no hosting and no CDN.

- **Development:** `npm run dev` in `web/` starts Vite on 5173 and sends `/api` to the U4 server on 127.0.0.1:8000.
- **Demo:** `npm run build` writes `web/dist`. U4's `create_app()` serves `web/dist` at `/` when the folder exists, falling back to `index.html` for SPA routes. One command, `python -m brahma.server`, then runs the whole app on 127.0.0.1:8000.
- `web/node_modules` and `web/dist` are gitignored.
- **Cost:** none.
