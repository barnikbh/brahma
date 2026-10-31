import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "@/api/client";
import { DISCLAIMER } from "@/api/types";
import { Banner } from "@/components/Banner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { useSession } from "@/state/session";

/** Screen 02: accept "Decision support, not diagnosis" before first use (BR1.3, FR15.1). */
export function DisclaimerPage() {
  const { session, acceptDisclaimer } = useSession();
  const navigate = useNavigate();
  const [understood, setUnderstood] = useState(false);
  const [synthetic, setSynthetic] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const accept = async () => {
    setSaving(true);
    setError(null);
    try {
      await acceptDisclaimer();
      navigate("/patients");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Acceptance failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mx-auto max-w-2xl py-8" aria-labelledby="disclaimer-title">
      <h1 id="disclaimer-title" className="font-serif text-3xl text-brand-900">
        {DISCLAIMER}
      </h1>
      <p className="mt-3">
        {session?.disclaimer.text ??
          `${DISCLAIMER}. Brahma shows cited knowledge-graph content for synthetic cases only.`}
      </p>
      <p className="mt-2 text-sm text-ink-quiet">
        Live knowledge packs: {session?.packVersions || "none loaded"}
      </p>
      <div className="mt-6 space-y-3 rounded-card border border-neutral-300 bg-white p-4">
        <div className="flex items-start gap-3">
          <Checkbox
            id="understood"
            checked={understood}
            onCheckedChange={(v) => setUnderstood(v === true)}
          />
          <label htmlFor="understood">
            I understand Brahma is decision support, not diagnosis, and that I decide.
          </label>
        </div>
        <div className="flex items-start gap-3">
          <Checkbox
            id="synthetic"
            checked={synthetic}
            onCheckedChange={(v) => setSynthetic(v === true)}
          />
          <label htmlFor="synthetic">
            I will enter synthetic cases only: no real patient names, IDs or records.
          </label>
        </div>
      </div>
      {error ? (
        <Banner role="alert" className="mt-4">
          {error}
        </Banner>
      ) : null}
      <Button
        className="mt-6"
        disabled={!understood || !synthetic || saving}
        onClick={() => void accept()}
      >
        {error ? "Retry" : "Accept and continue"}
      </Button>
    </section>
  );
}
