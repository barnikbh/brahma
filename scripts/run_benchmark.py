"""Lean benchmark (U7, FR13): Brahma graph vs the same model without it.

Run from the repository root with the live provider configured::

    set -a && source .env && set +a && .venv/bin/python scripts/run_benchmark.py

For each case in ``results/benchmark_cases.json`` the runner drives a full HTTP
walk (graph arm) and asks the same model the same question with only the pack's
source titles (plain arm, purpose ``plain_benchmark``). Every line is judged by
the pack's own claim check; agreement compares backing nodes against the
expected pathway, which is derived deterministically from the pack's traversal
(no hand-written answers). Writes ``results/benchmark.json`` (after every case,
so ``--resume`` never repeats one) and ``results/benchmark.html``.

``--expected-only`` prints each case's expected pathway without touching a model,
for the clinical reviewer. ``--cases id1,id2`` runs a subset.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from pydantic import BaseModel, ConfigDict, Field

import live_rehearsal
import live_walk
from brahma.agent.scanner import ClaimScanner
from brahma.agent.traverse import walk_graph
from brahma.bench import agreement, graph_grounded_share, judge_plain_line
from brahma.knowledge.db import kg_connect
from brahma.knowledge.matcher import normalise_text
from brahma.knowledge.models import Fact, Node, PackVersionRef
from brahma.knowledge.repository import KnowledgeRepository, version_id
from brahma.knowledge.service import KnowledgeService
from brahma.platform.db import pf_connect
from brahma.platform.errors import ModelError
from brahma.platform.models import ModelGateway, ModelRequest
from brahma.platform.models.config import ProviderConfig
from brahma.server.services import load_initial_packs

ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "results" / "benchmark_cases.json"
RESULTS_PATH = ROOT / "results" / "benchmark.json"
REPORT_PATH = ROOT / "results" / "benchmark.html"
T0 = time.time()

# FR13.2: a recommendation names one of these; agreement counts them.
RECOMMENDATION_TYPES = frozenset(
    {
        "diagnosis",
        "test",
        "subtype",
        "treatment_tier",
        "drug",
        "monitoring",
        "response_criterion",
        "escalation",
        "diet",
        "watch_out",
    }
)

PLAIN_SYSTEM = (
    "You answer a clinical workup question directly from your own medical knowledge "
    "(decision support, not diagnosis). Write one recommendation per line: a diagnosis, "
    "test, subtype, treatment, monitoring threshold or escalation trigger. For each "
    "line, cite the pack source it comes from by source ID, using only the listed "
    "sources; never invent source IDs. Return JSON only, matching the schema."
)


class PlainLine(BaseModel):
    """One plain-arm recommendation line with its cited pack sources."""

    model_config = ConfigDict(populate_by_name=True)

    text: str
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")


class PlainOutput(BaseModel):
    """The plain arm's cited pathway."""

    lines: list[PlainLine]


def log(msg: str) -> None:
    print(f"[+{time.time() - T0:7.1f}s] {msg}", flush=True)


def load_cases(path: Path, only: set[str] | None) -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    if only:
        cases = [c for c in cases if c["id"] in only]
        missing = only - {c["id"] for c in cases}
        if missing:
            raise SystemExit(f"unknown case ids: {sorted(missing)}")
    return cases


class BenchKnowledge:
    """Pack data for expected pathways and judging, on an isolated scratch database."""

    def __init__(self) -> None:
        self.path = Path(tempfile.mkdtemp(prefix="bench-kg-")) / "bench.db"
        kg_conn = kg_connect(self.path)
        self.knowledge = KnowledgeService(kg_conn)
        loaded = load_initial_packs(self.knowledge, ROOT / "content")
        log(f"knowledge: {', '.join(loaded)}")
        self.repo = KnowledgeRepository(kg_connect(self.path))
        self.scanner = ClaimScanner(self.knowledge)

    def live(self, pack: str) -> PackVersionRef:
        return self.knowledge.live_version(pack)

    def nodes(self, pack: str) -> list[Node]:
        ref = self.live(pack)
        return self.repo.read_nodes(version_id(ref.pack, ref.number))

    def node_map(self, pack: str) -> dict[str, Node]:
        return {n.node_id: n for n in self.nodes(pack)}

    def test_names(self, pack: str) -> dict[str, str]:
        return {
            n.node_id: str(n.fields["name"])
            for n in self.nodes(pack)
            if n.type == "test" and "name" in n.fields
        }

    def sources(self, pack: str) -> list[tuple[str, str, int]]:
        return [(s.source_id, s.title, s.year) for s in self.repo.read_sources(pack)]


def case_facts(case: dict[str, Any], test_names: dict[str, str]) -> list[Fact]:
    facts = [
        Fact(kind="finding", name=f["name"], value=f.get("value"), unit=f.get("unit"))
        for f in case["findings"]
    ]
    for node_id, value in case["answers"].items():
        facts.append(Fact(kind="test", name=test_names[node_id], value=value))
    return facts


def expected_pathway(bk: BenchKnowledge, case: dict[str, Any]) -> list[str]:
    """Expected recommendation nodes: deterministic traversal of the authored facts."""
    pack = case["pack"]
    facts = case_facts(case, bk.test_names(pack))
    trav = walk_graph(bk.knowledge, bk.live(pack), facts)
    if trav.outcome != "walked":
        raise SystemExit(f"case {case['id']}: traversal {trav.outcome} (check the findings)")
    nodes = bk.node_map(pack)
    return sorted(
        {n for ids in trav.sections.values() for n in ids if nodes[n].type in RECOMMENDATION_TYPES}
    )


def validate_case(bk: BenchKnowledge, case: dict[str, Any]) -> list[list[str]]:
    """Simulate the needs-data rounds; fail fast when an answer is missing."""
    test_names = bk.test_names(case["pack"])
    facts = [
        Fact(kind="finding", name=f["name"], value=f.get("value"), unit=f.get("unit"))
        for f in case["findings"]
    ]
    rounds: list[list[str]] = []
    for _ in range(6):
        trav = walk_graph(bk.knowledge, bk.live(case["pack"]), facts)
        if trav.outcome != "walked":
            raise SystemExit(f"case {case['id']}: traversal {trav.outcome} (check the findings)")
        if not trav.needed_tests:
            return rounds
        missing = [n for n in trav.needed_tests if n not in case["answers"]]
        if missing:
            raise SystemExit(f"case {case['id']}: no answers for {missing}")
        rounds.append(list(trav.needed_tests))
        facts += [
            Fact(kind="test", name=test_names[n], value=case["answers"][n])
            for n in trav.needed_tests
        ]
    raise SystemExit(f"case {case['id']}: needs did not settle")


def run_graph_arm(
    client: httpx.Client, case: dict[str, Any], expected: list[str]
) -> dict[str, Any]:
    """Full HTTP walk; grounded share from its counts, agreement from cited nodes."""
    result = live_walk.run_case_walk(client, case["patient"], case["text"], case["answers"])
    if not result["ok"]:
        return {"error": result["reason"], "grounded": None, "agreement": None}
    done = result["done"]
    counts = done.get("counts", {})
    cited = sorted({n for line in result["lines"] for n in line.get("nodeIds", [])})
    authored = {normalise_text(f["name"]) for f in case["findings"]}
    extracted = {normalise_text(f.get("name", "")) for f in result["extracted"]}
    return {
        "outcome": done.get("outcome"),
        "counts": counts,
        "cited": cited,
        "extractMatched": len(authored & extracted),
        "extractTotal": len(authored),
        "grounded": graph_grounded_share(counts.get("cited", 0), counts.get("ungrounded", 0)),
        "agreement": agreement(set(cited), set(expected)),
    }


def plain_prompt(
    case: dict[str, Any], test_names: dict[str, str], sources: list[tuple[str, str, int]]
) -> str:
    known = "\n".join(f"- {test_names[n]}: {v}" for n, v in case["answers"].items())
    listed = "\n".join(f"{sid}: {title} ({year})" for sid, title, year in sources)
    return (
        f"<case_data>\nPatient: {case['text']}\nKnown results:\n{known}\n</case_data>\n\n"
        f"Pack sources (titles only):\n{listed}\n\n"
        "Write the pathway as cited recommendation lines."
    )


def run_plain_arm(
    gateway: ModelGateway,
    bk: BenchKnowledge,
    case: dict[str, Any],
    expected: list[str],
) -> dict[str, Any]:
    """Same model, no graph, source titles only; every line judged by the claim check."""
    pack = case["pack"]
    version = bk.live(pack)
    nodes = bk.nodes(pack)
    by_source: dict[str, list[Node]] = {}
    for node in nodes:
        for source in node.source_ids:
            by_source.setdefault(source, []).append(node)
    test_names = bk.test_names(pack)
    request = ModelRequest(
        purpose="plain_benchmark",
        messages=[
            {"role": "system", "content": PLAIN_SYSTEM},
            {"role": "user", "content": plain_prompt(case, test_names, bk.sources(pack))},
        ],
        max_tokens=1500,
        response_schema=PlainOutput.model_json_schema(by_alias=True),
    )
    try:
        parsed = PlainOutput.model_validate(gateway.complete(request).parsed or {})
    except (ModelError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "grounded": None, "agreement": None}
    pack_sources = {s for s, _, _ in bk.sources(pack)}
    verdicts = []
    supporting: set[str] = set()
    for line in parsed.lines:
        claims = bk.scanner.scan(line.text, version)
        if not claims:
            verdicts.append({"text": line.text, "recommendation": False})
            continue
        verdict = judge_plain_line(claims, line.source_ids, by_source, pack_sources, nodes)
        supporting |= set(verdict.supporting)
        verdicts.append(
            {
                "text": line.text,
                "sources": line.source_ids,
                "recommendation": True,
                "grounded": verdict.grounded,
            }
        )
    recommendations = [v for v in verdicts if v["recommendation"]]
    grounded = (
        sum(1 for v in recommendations if v["grounded"]) / len(recommendations)
        if recommendations
        else None
    )
    return {
        "lines": verdicts,
        "recommendations": len(recommendations),
        "grounded": grounded,
        "agreement": agreement(supporting, set(expected)),
    }


def micro(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def verdict(totals: dict[str, Any]) -> str:
    """Pass iff the graph reaches 95% grounded on IBD and beats plain on both (FR13.6)."""
    ibd = totals["IBD"]
    graph_g, plain_g = ibd["graph_grounded"], ibd["plain_grounded"]
    graph_a, plain_a = ibd["graph_agreement"], ibd["plain_agreement"]
    if (
        graph_g is not None
        and graph_g >= 0.95
        and plain_g is not None
        and plain_a is not None
        and graph_g > plain_g
        and graph_a is not None
        and graph_a > plain_a
    ):
        return "Pass"
    return "Below 95%"


def write_report(results: dict[str, Any]) -> None:
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_PATH.write_text(render_html(results), encoding="utf-8")
    log(f"wrote {RESULTS_PATH} and {REPORT_PATH}")


def pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "—"


def render_html(results: dict[str, Any]) -> str:
    totals = results["totals"]
    rows = []
    for case in results["cases"]:
        graph = case["graph"]
        plain = case["plain"]
        rows.append(
            "<tr data-group='{_g}'>"
            "<td>{id}</td><td>{group}</td>"
            "<td>{gg}</td><td>{ga}</td><td>{pg}</td><td>{pa}</td>"
            "<td>{rec}</td><td>{review}</td></tr>".format(
                _g=html.escape(case["group"]),
                id=html.escape(case["id"]),
                group=html.escape(case["group"]),
                gg=pct(graph.get("grounded")),
                ga=pct(graph.get("agreement")),
                pg=pct(plain.get("grounded")),
                pa=pct(plain.get("agreement")),
                rec=plain.get("recommendations", "—"),
                review=html.escape(case.get("reviewedBy") or "pending"),
            )
        )
    arm_rows = []
    for label in ("IBD", "URO"):
        group = totals[label]
        arm_rows.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                label + ("" if label == "IBD" else " (shown, not counted)"),
                pct(group["graph_grounded"]),
                pct(group["graph_agreement"]),
                pct(group["plain_grounded"]),
                pct(group["plain_agreement"]),
            )
        )
    verdict_class = "verdict-pass" if results["verdict"] == "Pass" else "verdict-below"
    header = f"<h2 class='{verdict_class}'>{html.escape(results['verdict'])}</h2>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brahma benchmark: graph vs plain model</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto;
  padding: 0 1rem; color: #222; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left;
  font-size: 0.9rem; }}
th {{ background: #f4f4f4; }}
.verdict-pass {{ color: #0a7b2e; font-weight: bold; }}
.verdict-below {{ color: #a33; font-weight: bold; }}
details {{ margin: 1rem 0; }}
</style>
</head>
<body>
<h1>Brahma benchmark: graph vs plain model</h1>
<p>Model: {html.escape(results["model"])} &middot; Run: {html.escape(results["date"])} &middot;
Expected pathways: {html.escape(results["reviewStatus"])}</p>
{header}
<h2>Totals</h2>
<table><tr><th></th><th>Graph grounded</th><th>Graph agreement</th>
<th>Plain grounded</th><th>Plain agreement</th></tr>
{"".join(arm_rows)}</table>
<h2>Cases</h2>
<p><label>Group: <select id="group" onchange="filter()">
<option value="">All</option><option>UC</option><option>CD</option><option>URO</option>
</select></label></p>
<table id="cases"><tr><th>Case</th><th>Group</th><th>Graph grounded</th><th>Graph agreement</th>
<th>Plain grounded</th><th>Plain agreement</th><th>Plain recs</th><th>Reviewed by</th></tr>
{"".join(rows)}</table>
<script>
function filter() {{
  const g = document.getElementById('group').value;
  for (const r of document.querySelectorAll('#cases tr[data-group]'))
    r.style.display = (!g || r.dataset.group === g) ? '' : 'none';
}}
</script>
<details><summary>Methodology</summary>
<p>Each case runs twice on the same model: once as a full Brahma walk (graph arm),
once as a single answer with only the pack's source titles and no graph content
(plain arm). Graph grounded share is emitted lines over emitted plus held-back
lines from the walk's own counts. Plain grounded share is recommendation lines
whose cited pack source exists and whose every claim is supported by a node under
a cited source, using the same claim check as the walk guard. Agreement is backing
nodes (cited for graph, supporting for plain) hitting the expected pathway over
expected nodes. Expected pathways are derived deterministically from the pack's
traversal over each case's findings and answers — never hand-written. Uro cases
are shown but not counted toward the verdict.</p>
</details>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Lean benchmark: graph vs plain model.")
    parser.add_argument("--expected-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cases", default="")
    args = parser.parse_args()

    only = {c.strip() for c in args.cases.split(",") if c.strip()} or None
    cases = load_cases(CASES_PATH, only)
    bk = BenchKnowledge()

    for case in cases:
        rounds = validate_case(bk, case)
        expected = expected_pathway(bk, case)
        print(f"{case['id']}: needs={[','.join(r) for r in rounds]}")
        print(f"  expected ({len(expected)}): {', '.join(expected)}")
    if args.expected_only:
        return 0

    provider = ProviderConfig.from_env()
    model_name = f"{provider.provider}/{provider.model}"
    done: dict[str, Any] = {}
    if args.resume and RESULTS_PATH.exists():
        previous = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        if previous.get("model") != model_name:
            raise SystemExit(f"resume model {previous.get('model')} != {model_name}")
        done = {c["id"]: c for c in previous.get("cases", [])}
        log(f"resuming: {len(done)} cases already done")

    server, base, slog = live_rehearsal.start_on_free_port()
    try:
        client = httpx.Client(base_url=base, timeout=900.0)
        assert client.post("/api/session", json={"profileId": "p-maya"}).status_code == 200
        assert client.post("/api/disclaimer").status_code == 200
        gateway = ModelGateway.from_env(pf_connect(bk.path))
        results: list[dict[str, Any]] = []
        for case in cases:
            if case["id"] in done:
                log(f"{case['id']}: already done, skipping")
                results.append(done[case["id"]])
                continue
            log(f"{case['id']}: graph arm...")
            expected = expected_pathway(bk, case)
            graph = run_graph_arm(client, case, expected)
            log(f"{case['id']}: plain arm...")
            plain = run_plain_arm(gateway, bk, case, expected)
            results.append(
                {
                    "id": case["id"],
                    "group": case["group"],
                    "pack": case["pack"],
                    "reviewedBy": case.get("reviewedBy"),
                    "expected": expected,
                    "graph": graph,
                    "plain": plain,
                }
            )
            save(model_name, results, complete=False)
        save(model_name, results, complete=True)
        return 0
    finally:
        live_rehearsal.stop_server(server, slog)


def save(model_name: str, results: list[dict[str, Any]], complete: bool) -> None:
    totals = {}
    for label, groups in (("IBD", ("UC", "CD")), ("URO", ("URO",))):
        group_cases = [c for c in results if c["group"] in groups]
        totals[label] = {
            "graph_grounded": micro([c["graph"].get("grounded") for c in group_cases]),
            "graph_agreement": micro([c["graph"].get("agreement") for c in group_cases]),
            "plain_grounded": micro([c["plain"].get("grounded") for c in group_cases]),
            "plain_agreement": micro([c["plain"].get("agreement") for c in group_cases]),
        }
    reviewed = [c.get("reviewedBy") for c in results if c.get("reviewedBy")]
    output = {
        "model": model_name,
        "date": datetime.now(UTC).date().isoformat(),
        "complete": complete,
        "verdict": verdict(totals),
        "totals": totals,
        "reviewStatus": (
            f"{len(reviewed)}/{len(results)} cases reviewed" if reviewed else "pending review"
        ),
        "cases": results,
    }
    write_report(output)


if __name__ == "__main__":
    sys.exit(main())
