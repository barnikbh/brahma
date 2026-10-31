import { useEffect, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { setUnauthorizedHandler } from "@/api/client";
import { AppShell } from "@/components/AppShell";
import { DisclaimerPage } from "@/pages/DisclaimerPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { KnowledgePage } from "@/pages/KnowledgePage";
import { PatientsPage } from "@/pages/PatientsPage";
import { SignInPage } from "@/pages/SignInPage";
import { WorkspacePage } from "@/pages/WorkspacePage";
import { hasFeature, useSession } from "@/state/session";

/** Signed in, with the disclaimer accepted, or redirect (BR1). */
function RequireSession({
  children,
  disclaimer = false,
}: {
  children: ReactNode;
  disclaimer?: boolean;
}) {
  const { session, loading } = useSession();
  if (loading) {
    return (
      <p role="status" className="text-sm text-ink-quiet">
        Loading…
      </p>
    );
  }
  if (!session) return <Navigate to="/signin" replace />;
  if (session.needsDisclaimer && !disclaimer) return <Navigate to="/disclaimer" replace />;
  return <>{children}</>;
}

function Home() {
  const { session, loading } = useSession();
  if (loading) return null;
  return <Navigate to={session ? "/patients" : "/signin"} replace />;
}

function KnowledgeRoute() {
  const { features } = useSession();
  if (!hasFeature(features, "knowledge")) return <Navigate to="/patients" replace />;
  return <KnowledgePage />;
}

export function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const { clearSession } = useSession();

  // A 401 anywhere means the session is gone: forget it locally (no new request, so no
  // loop) and go to sign-in.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearSession();
      if (location.pathname !== "/signin") navigate("/signin");
    });
  }, [navigate, location.pathname, clearSession]);

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/signin" element={<SignInPage />} />
        <Route
          path="/disclaimer"
          element={
            <RequireSession disclaimer>
              <DisclaimerPage />
            </RequireSession>
          }
        />
        <Route
          path="/patients"
          element={
            <RequireSession>
              <PatientsPage />
            </RequireSession>
          }
        />
        <Route
          path="/cases/:caseId"
          element={
            <RequireSession>
              <WorkspacePage />
            </RequireSession>
          }
        />
        <Route
          path="/history/:sessionId?"
          element={
            <RequireSession>
              <HistoryPage />
            </RequireSession>
          }
        />
        <Route
          path="/knowledge"
          element={
            <RequireSession>
              <KnowledgeRoute />
            </RequireSession>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
