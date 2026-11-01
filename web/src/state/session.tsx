// Who is signed in, the live packs and the server's health, shared by every screen.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api } from "@/api/client";
import type { Feature, Health, SessionView } from "@/api/types";

export interface SessionState {
  session: SessionView | null;
  features: Feature[];
  health: Health | null;
  /** The server could not be reached (not running). */
  serverDown: boolean;
  loading: boolean;
  refresh: () => Promise<void>;
  signIn: (profileId: string) => Promise<SessionView>;
  signOut: () => Promise<void>;
  acceptDisclaimer: () => Promise<void>;
  refreshHealth: () => Promise<void>;
  /** Forget the session locally after a 401 (no request). */
  clearSession: () => void;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionView | null>(null);
  const [features, setFeatures] = useState<Feature[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [serverDown, setServerDown] = useState(false);
  const [loading, setLoading] = useState(true);

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await api.health());
      setServerDown(false);
    } catch (error) {
      if (error instanceof ApiError && error.status === 0) setServerDown(true);
    }
  }, []);

  const loadFeatures = useCallback(async () => {
    try {
      setFeatures((await api.features()).features);
    } catch {
      setFeatures([]);
    }
  }, []);

  // Loading starts true and only the first load clears it: a later refresh runs behind the
  // current screen, since showing "loading" would unmount the page and lose its state.
  const refresh = useCallback(async () => {
    await refreshHealth();
    try {
      const view = await api.session();
      setSession(view);
      await loadFeatures();
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, [refreshHealth, loadFeatures]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(
    async (profileId: string) => {
      const view = await api.signIn(profileId);
      setSession(view);
      await loadFeatures();
      return view;
    },
    [loadFeatures],
  );

  const signOut = useCallback(async () => {
    try {
      await api.signOut();
    } finally {
      setSession(null);
    }
  }, []);

  const acceptDisclaimer = useCallback(async () => {
    await api.acceptDisclaimer();
    setSession((current) => (current ? { ...current, needsDisclaimer: false } : current));
  }, []);

  const clearSession = useCallback(() => setSession(null), []);

  const value = useMemo<SessionState>(
    () => ({
      session,
      features,
      health,
      serverDown,
      loading,
      refresh,
      signIn,
      signOut,
      acceptDisclaimer,
      refreshHealth,
      clearSession,
    }),
    [
      clearSession,
      session,
      features,
      health,
      serverDown,
      loading,
      refresh,
      signIn,
      signOut,
      acceptDisclaimer,
      refreshHealth,
    ],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

/** True when the knowledge feature module is mounted (C7). */
export function hasFeature(features: Feature[], name: string): boolean {
  return features.some((f) => f.name === name);
}
