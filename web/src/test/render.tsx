import { render, type RenderResult } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "@/App";
import { SessionProvider } from "@/state/session";

/** Render the whole app at a route, inside the session provider and a memory router. */
export function renderApp(path: string): RenderResult {
  return render(
    <MemoryRouter
      initialEntries={[path]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <SessionProvider>
        <App />
      </SessionProvider>
    </MemoryRouter>,
  );
}
