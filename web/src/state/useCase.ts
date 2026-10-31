// Load a case (C8 CaseView) and drive its walk stream through the reducer.

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, api } from "@/api/client";
import type { CaseView, WalkRequest } from "@/api/types";
import { streamWalk } from "@/api/walkStream";
import { initialWalkState, walkReducer, type WalkAction, type WalkState } from "./walkReducer";

export interface UseCase {
  view: CaseView | null;
  loadError: ApiError | null;
  state: WalkState;
  dispatch: (action: WalkAction) => void;
  walk: (request: WalkRequest) => Promise<void>;
  reload: () => Promise<void>;
  setView: (view: CaseView) => void;
}

export function useCase(caseId: string | undefined): UseCase {
  const [view, setViewState] = useState<CaseView | null>(null);
  const [loadError, setLoadError] = useState<ApiError | null>(null);
  const [state, dispatch] = useReducer(walkReducer, initialWalkState);
  const abort = useRef<AbortController | null>(null);

  const setView = useCallback((next: CaseView) => {
    setViewState(next);
    dispatch({ type: "loaded", view: next });
  }, []);

  const reload = useCallback(async () => {
    if (!caseId) return;
    try {
      const next = await api.getCase(caseId);
      setLoadError(null);
      setView(next);
      if (next.walk) {
        const map = await api.caseMap(caseId);
        dispatch({ type: "map_loaded", map });
      }
    } catch (error) {
      setLoadError(error instanceof ApiError ? error : new ApiError(0, "unknown", String(error)));
    }
  }, [caseId, setView]);

  useEffect(() => {
    void reload();
    return () => abort.current?.abort();
  }, [reload]);

  const walk = useCallback(
    async (request: WalkRequest) => {
      if (!caseId) return;
      abort.current?.abort();
      const controller = new AbortController();
      abort.current = controller;
      dispatch({ type: "request", request });
      try {
        await streamWalk(
          caseId,
          request,
          (event) => dispatch({ type: "event", event }),
          controller.signal,
        );
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        const apiError =
          error instanceof ApiError ? error : new ApiError(0, "unknown", String(error), true);
        dispatch({
          type: "request_failed",
          error: { code: apiError.code, message: apiError.message, retryable: apiError.retryable },
        });
      }
    },
    [caseId],
  );

  return { view, loadError, state, dispatch, walk, reload, setView };
}
