import { defineConfig, devices } from "@playwright/test";

// Local smoke test of the demo walk (team practice: no hosted URL). Playwright starts the
// real U4 server with the recorded provider (no keys, no network) on a fresh SQLite file,
// serving the built app from web/dist. Run `npm run build` first.
const PORT = Number(process.env.E2E_PORT ?? 8000);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
  ],
  webServer: {
    command:
      "rm -f data/e2e.db data/e2e.db-wal data/e2e.db-shm && .venv/bin/python -m brahma.server",
    cwd: "..",
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      BRAHMA_MODEL_PROVIDER: "recorded",
      BRAHMA_RECORDED_DIR: "tests/agent/fixtures/recorded/demo",
      BRAHMA_DB_PATH: "data/e2e.db",
      BRAHMA_LOG_PATH: "data/e2e.log",
      BRAHMA_PORT: String(PORT),
    },
  },
});
