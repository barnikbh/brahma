# Tech Stack Decisions — u8-web-app

Upstream: `functional-spec.md` and `frontend-components.md` (U8), `requirements.md` (NFR9, NFR12), team practices (Code Style, Testing Posture).

- **Build:** Vite + React 18 + TypeScript (`strict`) in the `web/` folder, with npm as the package manager.
  - In development, the Vite proxy sends `/api` to `127.0.0.1:8000`.
  - For the demo, `npm run build` puts its output in `web/dist`, and U4's server serves that folder, so there is one URL and one command.
  - Alternative considered: Next.js. Rejected because it is heavier and its server rendering isn't needed.
- **User interface:** Tailwind CSS and shadcn/ui components, copied into the source. The map uses React Flow (`@xyflow/react`). Routing uses `react-router`.
- **Quality:**
  - ESLint and Prettier, as the team practice requires.
  - Vitest and React Testing Library, with an 80% line-coverage floor on `web/src`.
  - A Playwright smoke test of the demo walk against the locally running app, using the recorded provider (NFR9).
- **Setup:** Node 20 or newer. The README covers `npm ci` and `npm run build` (NFR10).
