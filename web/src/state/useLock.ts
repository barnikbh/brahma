// The one-tab case lock (BR3.9, BR4.3): heartbeat every 15 s, release it when the tab
// closes or the workspace unmounts. Loading the case (GET with X-Brahma-Tab) takes the lock
// first; the hook starts once `enabled` (the case is loaded). A heartbeat is skipped while
// another request runs, because the server shares one database connection across threads.

import { useEffect, useState } from "react";
import { api, requestsInFlight } from "@/api/client";
import type { LockState } from "@/api/types";

export const HEARTBEAT_MS = 15_000;

export type LockStatus = LockState | "pending";

export function useLock(caseId: string | undefined, enabled = true): LockStatus {
  const [state, setState] = useState<LockStatus>("pending");

  useEffect(() => {
    if (!caseId || !enabled) return undefined;
    let active = true;
    const beat = () => {
      if (requestsInFlight() > 0) return;
      api
        .lock(caseId)
        .then((result) => {
          if (active) setState(result.state);
        })
        .catch(() => {
          // A failed heartbeat keeps the last known state; the next beat tries again.
        });
    };
    const release = () => {
      api.unlock(caseId).catch(() => undefined);
    };
    beat();
    const timer = window.setInterval(beat, HEARTBEAT_MS);
    window.addEventListener("beforeunload", release);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("beforeunload", release);
      release();
    };
  }, [caseId, enabled]);

  return state;
}
