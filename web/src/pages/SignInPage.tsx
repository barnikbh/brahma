import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "@/api/client";
import type { Profile } from "@/api/types";
import { Banner } from "@/components/Banner";
import { Button } from "@/components/ui/button";
import { useSession } from "@/state/session";

const ROLE_LABEL: Record<string, string> = {
  doctor: "Doctor",
  reviewer: "Clinical reviewer",
  system: "System",
};

/** Screen 01: pick a demo profile; no password (BR1.1). */
export function SignInPage() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setProfiles((await api.profiles()).profiles.filter((p) => p.listed !== false));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Profiles failed to load.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const pick = async (profile: Profile) => {
    setBusy(profile.profileId);
    setError(null);
    try {
      const view = await signIn(profile.profileId);
      navigate(view.needsDisclaimer ? "/disclaimer" : "/patients");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Sign-in failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="mx-auto max-w-3xl py-8" aria-labelledby="signin-title">
      <h1 id="signin-title" className="font-serif text-3xl text-brand-900">
        Sign in
      </h1>
      <p className="mt-1 text-ink-quiet">
        Pick a demo profile. These are demo identities for synthetic cases; there is no password.
      </p>
      {error ? (
        <Banner
          role="alert"
          className="mt-4"
          actions={
            <Button size="sm" variant="outline" onClick={() => void load()}>
              Retry
            </Button>
          }
        >
          {error}
        </Banner>
      ) : null}
      <ul className="mt-6 grid grid-cols-3 gap-4">
        {(profiles ?? []).map((profile) => (
          <li key={profile.profileId}>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void pick(profile)}
              className="flex h-full w-full flex-col items-start gap-1 rounded-card border border-neutral-300 bg-white p-4 text-left hover:border-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2 disabled:opacity-60"
            >
              <span className="font-semibold">{profile.displayName}</span>
              <span className="text-sm text-ink-quiet">
                {ROLE_LABEL[profile.role] ?? profile.role}
                {profile.specialty ? ` · ${profile.specialty}` : ""}
              </span>
              {profile.demoRegistration ? (
                <span className="font-mono text-xs text-ink-quiet">{profile.demoRegistration}</span>
              ) : null}
              <span className="mt-2 text-sm text-brand-700">
                {busy === profile.profileId ? "Signing in…" : "Sign in →"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
