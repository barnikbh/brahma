# Monitoring Design — u8-web-app

Upstream: `performance-design.md` and `security-design.md` (U8), `functional-spec.md` (U8).

- **Health:** the shell calls `/api/health` once at start. If it fails, the shell shows "Brahma server isn't running" with a Retry button.
- **Error rate:** the server log (U4) records walk errors. In the browser, the API client logs any non-2xx response to the console with its error code. It never logs patient values.
- **Alerting:** none. This is a local demo.
