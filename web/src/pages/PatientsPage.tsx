import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "@/api/client";
import type { CaseStatus, CaseSummary, Sex } from "@/api/types";
import { Banner } from "@/components/Banner";
import { Synthetic } from "@/components/Synthetic";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { formatWhen, splitList } from "@/lib/utils";

export const SEARCH_DEBOUNCE_MS = 250;

const STATUS: Record<CaseStatus, { label: string; variant: BadgeProps["variant"] }> = {
  new: { label: "◌ New", variant: "quiet" },
  needs_data: { label: "? Needs data", variant: "pending" },
  answered: { label: "✓ Answered", variant: "ok" },
  out_of_knowledge: { label: "⊘ Out of knowledge", variant: "quiet" },
  follow_up_due: { label: "◷ Follow-up due", variant: "quiet" },
};

export function StatusChip({ status }: { status: CaseStatus }) {
  const look = STATUS[status] ?? STATUS.new;
  return <Badge variant={look.variant}>{look.label}</Badge>;
}

/** Screen 03: find, create or reopen a synthetic patient (BR2). */
export function PatientsPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const q = query.trim();
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .searchPatients(q, controller.signal)
        .then((r) => {
          setResults(r.results);
          setError(null);
        })
        .catch((e: unknown) => {
          if (e instanceof DOMException && e.name === "AbortError") return;
          setError(e instanceof ApiError ? e.message : "Search failed.");
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, attempt]);

  return (
    <section aria-labelledby="patients-title" className="mx-auto max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 id="patients-title" className="font-serif text-2xl text-brand-900">
          Patients
        </h1>
        <Button onClick={() => setCreating(true)}>Create new patient</Button>
      </div>
      <label htmlFor="patient-search" className="mt-4 block text-sm font-medium">
        Search by case ID, finding or diagnosis
      </label>
      <Input
        id="patient-search"
        type="search"
        value={query}
        maxLength={200}
        placeholder="e.g. BR-000123, bloody stool, ulcerative colitis"
        onChange={(e) => setQuery(e.target.value)}
        className="mt-1"
      />
      {error ? (
        <Banner
          role="alert"
          className="mt-3"
          actions={
            <Button size="sm" variant="outline" onClick={() => setAttempt((a) => a + 1)}>
              Retry
            </Button>
          }
        >
          {error}
        </Banner>
      ) : null}
      {creating ? (
        <CreatePatient
          onCancel={() => setCreating(false)}
          onCreated={(caseId) => navigate(`/cases/${caseId}`)}
        />
      ) : null}
      {results && results.length === 0 && !query.trim() && !creating ? (
        <p className="mt-6 text-sm text-ink-quiet">
          No patients yet. Create a new synthetic patient to begin.
        </p>
      ) : null}
      {results && results.length === 0 && query.trim() ? (
        <div className="mt-6 rounded-card border border-neutral-300 bg-white p-6 text-center">
          <p className="font-medium">No patients found</p>
          <Button className="mt-3" variant="outline" onClick={() => setCreating(true)}>
            Create new patient
          </Button>
        </div>
      ) : null}
      {results && results.length > 0 ? (
        <h2 className="mt-4 text-sm font-medium text-ink-quiet">
          {query.trim() ? "Matching patients" : "Recent patients"}
        </h2>
      ) : null}
      {results && results.length > 0 ? (
        <ul className="mt-2 divide-y divide-neutral-200 rounded-card border border-neutral-300 bg-white">
          {results.map((r) => (
            <li key={r.caseId}>
              <button
                type="button"
                onClick={() => navigate(`/cases/${r.caseId}`)}
                className="flex w-full items-center gap-4 px-4 py-3 text-left hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
              >
                <span className="font-medium">
                  <Synthetic>{r.syntheticName}</Synthetic>
                </span>
                <span className="font-mono text-xs text-ink-quiet">{r.caseId}</span>
                <StatusChip status={r.status} />
                <span className="ml-auto text-xs text-ink-quiet">{formatWhen(r.updatedAt)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function CreatePatient({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: (caseId: string) => void;
}) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<Sex>("female");
  const [weight, setWeight] = useState("");
  const [allergies, setAllergies] = useState("");
  const [comorbidities, setComorbidities] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const view = await api.createPatient({
        syntheticName: name.trim(),
        age: Number(age),
        sex,
        weightKg: weight.trim() ? Number(weight) : null,
        allergies: splitList(allergies),
        comorbidities: splitList(comorbidities),
      });
      onCreated(view.case.caseId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The patient could not be created.");
      setSaving(false);
    }
  };

  return (
    <form
      aria-labelledby="create-title"
      onSubmit={(e) => void submit(e)}
      className="mt-4 grid grid-cols-2 gap-3 rounded-card border-2 border-brand-900 bg-white p-4"
    >
      <h2 id="create-title" className="col-span-2 font-semibold">
        New synthetic patient
      </h2>
      <label className="text-sm">
        Synthetic name
        <Input
          required
          maxLength={80}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Demo Patient A"
        />
      </label>
      <label className="text-sm">
        Age (years)
        <Input
          required
          type="number"
          min={0}
          max={130}
          value={age}
          onChange={(e) => setAge(e.target.value)}
        />
      </label>
      <label className="text-sm">
        Sex
        <Select value={sex} onChange={(e) => setSex(e.target.value as Sex)}>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="unknown">Unknown</option>
        </Select>
      </label>
      <label className="text-sm">
        Weight (kg)
        <Input
          type="number"
          min={1}
          step="0.1"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
        />
      </label>
      <label className="text-sm">
        Allergies (comma separated)
        <Input value={allergies} onChange={(e) => setAllergies(e.target.value)} />
      </label>
      <label className="text-sm">
        Comorbidities (comma separated)
        <Input value={comorbidities} onChange={(e) => setComorbidities(e.target.value)} />
      </label>
      {error ? (
        <p role="alert" className="col-span-2 text-sm text-result-bad">
          ! {error}
        </p>
      ) : null}
      <div className="col-span-2 flex gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? "Creating…" : "Create and open"}
        </Button>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
