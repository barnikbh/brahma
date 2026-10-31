import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { SERVER_DOWN_MESSAGE } from "@/api/client";
import { DISCLAIMER } from "@/api/types";
import { Banner } from "@/components/Banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, packChips } from "@/lib/utils";
import { hasFeature, useSession } from "@/state/session";

/**
 * The header on every screen: wordmark, navigation, the live pack chip(s), the profile
 * and the "Decision support, not diagnosis" bar (FR15.1, BR1.2). Below 1280 px a notice
 * says the app is built for desktop screens.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { session, features, health, serverDown, refresh, signOut } = useSession();
  const navigate = useNavigate();
  const chips = session
    ? packChips(session.packVersions)
    : packChips((health?.packs ?? []).map((p) => `${p.pack} ${p.number}`));
  const signedIn = Boolean(session) && !session?.needsDisclaimer;

  const links = [
    { to: "/patients", label: "Patients" },
    { to: "/history", label: "History" },
    ...(hasFeature(features, "knowledge") ? [{ to: "/knowledge", label: "Knowledge" }] : []),
  ];

  return (
    <div className="min-h-screen bg-sage-page font-sans text-base text-ink">
      <header className="border-b border-neutral-200 bg-white">
        <div className="flex items-center gap-6 px-6 py-3">
          <div className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-900 font-serif text-lg text-white"
            >
              B
            </span>
            <div className="leading-tight">
              <div className="font-serif text-lg text-brand-900">Brahma</div>
              <div className="text-xs text-ink-quiet">Clinical decision graph</div>
            </div>
          </div>
          {signedIn ? (
            <nav aria-label="Main" className="flex gap-1">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    cn(
                      "rounded-md px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700",
                      isActive ? "bg-brand-900 text-white" : "text-ink hover:bg-brand-50",
                    )
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          ) : null}
          <div className="ml-auto flex items-center gap-3">
            <div aria-label="Live knowledge packs" className="flex gap-1">
              {chips.map((chip) => (
                <Badge key={chip} variant="default" className="font-mono" data-testid="pack-chip">
                  {chip}
                </Badge>
              ))}
            </div>
            {session ? (
              <>
                <span className="text-sm" data-testid="profile-name">
                  {session.profile.displayName}
                </span>
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => {
                    void signOut().then(() => navigate("/signin"));
                  }}
                >
                  Sign out
                </Button>
              </>
            ) : null}
          </div>
        </div>
        <div
          className="flex items-center gap-2 border-t border-sage-line bg-sage-note px-6 py-1.5 text-sm text-sage-ink"
          data-testid="disclaimer-bar"
        >
          <span aria-hidden="true">ⓘ</span>
          <strong>{DISCLAIMER}.</strong>
          <span>
            Synthetic patients only. Every line comes from the knowledge graph, never from the
            model&apos;s memory.
          </span>
        </div>
      </header>
      <div className="hidden px-6 pt-3 max-[1279px]:block" data-testid="desktop-only">
        <Banner>Brahma is built for desktop screens (1280 px and up).</Banner>
      </div>
      {serverDown ? (
        <div className="px-6 pt-3">
          <Banner
            role="alert"
            actions={
              <Button size="sm" variant="outline" onClick={() => void refresh()}>
                Retry
              </Button>
            }
          >
            {SERVER_DOWN_MESSAGE}
          </Banner>
        </div>
      ) : null}
      <main className="px-6 py-4">{children}</main>
    </div>
  );
}
