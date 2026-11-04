"""Walk every seeded test case against a running server on the live model.

Run from the repository root after ``scripts/seed_test_cases.py``, with the server
running on the live provider (default http://127.0.0.1:8000)::

    .venv/bin/python scripts/live_test_cases.py            # every case
    .venv/bin/python scripts/live_test_cases.py T02 U01    # only these

For each test patient it plays the doctor's steps from ``docs/test-cases.md`` through
the same API the web app uses, and records what came back: every Server-Sent Event,
which screen component draws it, the extracted finding chips, the forms, the cited
lines, the map statuses and the summary. It then checks the expected results and
writes ``results/live-test-cases.json`` and ``results/live-test-cases.md``.

The cases are left walked in the database, so each one can be opened in the app
afterwards. No clinical text goes to the server log; the report files hold the
synthetic cases' lines and are written locally only.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("BRAHMA_REHEARSAL_BASE", "http://127.0.0.1:8000")
TAB = "tab-live-cases"
HEADERS = {"X-Brahma-Tab": TAB}
OUT_JSON = ROOT / "results" / "live-test-cases.json"
OUT_MD = ROOT / "results" / "live-test-cases.md"
IBD = "IBD@1.2"

# Which web component draws each walk event (web/src/components, pages).
COMPONENT = {
    "progress": "ChatThread progress line",
    "form": "ChatForm (confirm-findings chips / needs-data)",
    "paused": "ChatForm waiting state",
    "line": "ChatLine + NodeChip (cited line)",
    "section_done": "ChatThread section header",
    "map_update": "GraphCanvas (map)",
    "done": "WalkSummary + ResultBadge",
    "history": "ChatThread notice (treatment history)",
    "reviewed": "ChatThread notice (day-3 review)",
    "lane_closed": "GraphCanvas explore lane",
    "error": "ChatThread error with Retry",
}
UC = {"IBD-N20": "negative", "IBD-N21": "ulcerative colitis", "IBD-N22": "E3", "IBD-N23": "severe"}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[+{time.time() - T0:7.1f}s] {msg}", flush=True)


Events = list[tuple[str, dict[str, Any]]]


def of(events: Events, kind: str) -> list[dict[str, Any]]:
    return [p for name, p in events if name == kind]


@dataclass
class Run:
    """One case's recorded steps and checks."""

    tid: str
    case_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def check(self, label: str, ok: bool, got: Any = None) -> None:
        self.checks.append({"check": label, "pass": bool(ok), "got": got})
        log(f"  {'PASS' if ok else 'FAIL'} {label}" + ("" if ok else f" (got {got!r})"))


class Api:
    """The web app's calls, over HTTP, with each walk stream recorded."""

    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def sign_in(self, profile: str) -> None:
        assert self.client.post("/api/session", json={"profileId": profile}).status_code == 200
        assert self.client.post("/api/disclaimer").status_code == 200

    def stream(self, run: Run, action: str, body: dict[str, Any]) -> Events:
        events: Events = []
        event, data, started = "", "", time.time()
        url = f"/api/cases/{run.case_id}/walk"
        with self.client.stream("POST", url, json=body, headers=HEADERS) as resp:
            if resp.status_code != 200:
                text = resp.read().decode()[:400]
                run.steps.append({"action": action, "http": resp.status_code, "body": text})
                raise RuntimeError(f"{action}: HTTP {resp.status_code} {text}")
            for raw in resp.iter_lines():
                line = raw.strip()
                if not line:
                    if event:
                        events.append((event, json.loads(data or "{}")))
                    event, data = "", ""
                elif line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
        run.steps.append(step_record(action, body, events, time.time() - started))
        return events

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        resp = self.client.get(path, params=params or None, headers=HEADERS)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    def call(self, run: Run, action: str, method: str, path: str, body: Any) -> httpx.Response:
        started = time.time()
        resp = self.client.request(method, path, json=body, headers=HEADERS)
        run.steps.append(
            {
                "action": action,
                "request": body,
                "http": resp.status_code,
                "seconds": round(time.time() - started, 2),
                "response": _trim(resp.json() if resp.content else None),
            }
        )
        return resp

    def map_status(self, run: Run) -> dict[str, str]:
        nodes = self.get(f"/api/cases/{run.case_id}/map").get("nodes", [])
        return {n["nodeId"]: n["status"] for n in nodes}

    def map_labels(self, run: Run, status: str) -> list[str]:
        nodes = self.get(f"/api/cases/{run.case_id}/map").get("nodes", [])
        return [n["label"] for n in nodes if n["status"] == status]

    def node(self, run: Run, node_id: str, version: str = IBD) -> dict[str, Any]:
        return self.get(f"/api/nodes/{version}/{node_id}", caseId=run.case_id)


def _trim(value: Any) -> Any:
    text = json.dumps(value, ensure_ascii=False)
    return value if len(text) < 3000 else text[:3000] + "…"


def step_record(
    action: str, body: dict[str, Any], events: Events, seconds: float
) -> dict[str, Any]:
    """What one walk call returned, grouped by the component that draws it."""
    counts = Counter(name for name, _ in events)
    forms = [
        {
            "kind": p.get("kind"),
            "fields": [
                {
                    k: f.get(k)
                    for k in (
                        "name",
                        "label",
                        "findingKind",
                        "value",
                        "unit",
                        "duration",
                        "nodeId",
                        "options",
                        "validationState",
                    )
                    if f.get(k) not in (None, [], "")
                }
                for f in p.get("fields", [])
            ],
        }
        for p in of(events, "form")
    ]
    return {
        "action": action,
        "request": {k: v for k, v in body.items() if k != "formValues"}
        | ({"formValues": body["formValues"]} if "formValues" in body else {}),
        "seconds": round(seconds, 1),
        "events": dict(counts),
        "components": sorted({COMPONENT.get(name, name) for name in counts}),
        "progress": [p.get("step") for p in of(events, "progress")],
        "forms": forms,
        "lines": [
            {"section": p.get("sectionId"), "text": p.get("text"), "nodeIds": p.get("nodeIds")}
            for p in of(events, "line")
        ],
        "notices": [p.get("text") for p in of(events, "history") + of(events, "reviewed")],
        "done": of(events, "done")[-1] if of(events, "done") else None,
        "errors": of(events, "error"),
    }


def findings_from(form: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "kind": f.get("findingKind"),
            "name": f.get("name"),
            "value": f.get("value"),
            "unit": f.get("unit"),
            "duration": f.get("duration"),
        }
        for f in form.get("fields", [])
    ]


def walk_through(
    api: Api,
    run: Run,
    first: Events,
    answers: dict[str, str],
    fix_findings: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
) -> Events:
    """Answer each form the walk posts until it ends; returns every event."""
    events = list(first)
    step = first
    asked: set[tuple[str, ...]] = set()
    for _ in range(8):
        if of(step, "done") or of(step, "error") or not of(step, "form"):
            break
        form = of(step, "form")[-1]
        if form.get("kind") == "confirm-findings":
            found = findings_from(form)
            values: dict[str, Any] = {"findings": fix_findings(found) if fix_findings else found}
            action = "confirm findings"
        else:
            keys = tuple(str(f.get("nodeId") or f.get("name")) for f in form.get("fields", []))
            if keys in asked:
                break
            asked.add(keys)
            values = {k: answers.get(k, "") for k in keys}
            action = "answer needs-data " + ", ".join(
                f"{k}={v or '(blank)'}" for k, v in values.items()
            )
        step = api.stream(
            run,
            action,
            {
                "mode": "continue",
                "walkId": form["walkId"],
                "formMessageId": form["messageId"],
                "formValues": values,
            },
        )
        events += step
    return events


def start(api: Api, run: Run, text: str, answers: dict[str, str], **kw: Any) -> Events:
    first = api.stream(run, "start walk", {"mode": "start", "text": text})
    return walk_through(api, run, first, answers, **kw)


def done_of(events: Events) -> dict[str, Any]:
    dones = of(events, "done")
    return dones[-1] if dones else {}


def walk_ok(run: Run, events: Events, outcome: str = "answered") -> dict[str, Any]:
    done = done_of(events)
    run.check(f"walk ends {outcome}", done.get("outcome") == outcome, done.get("outcome"))
    if outcome == "answered":
        ungrounded = done.get("counts", {}).get("ungrounded")
        run.check("0 ungrounded lines (1 tolerated live)", ungrounded in (0, 1), ungrounded)
    return done


def entry_has(api: Api, run: Run, label: str) -> None:
    entries = api.map_labels(run, "entry")
    run.check(f"Start here is {label}", any(label in e for e in entries), entries)


# --- the cases ---------------------------------------------------------------------------


def t01(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    entry_has(api, run, "UC Tier 2")
    resp = api.call(
        run,
        "choose Hydrocortisone",
        "POST",
        f"/api/cases/{run.case_id}/traverse",
        {"nodeId": "IBD-N51"},
    )
    body = resp.json()
    run.check(
        "Choose this option -> Now on card",
        resp.status_code == 201 and body.get("path", {}).get("drug", {}).get("nodeId") == "IBD-N51",
        body.get("notice"),
    )
    run.check("Hydrocortisone shows Chosen", api.map_status(run).get("IBD-N51") == "chosen")


def t02(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    detail = api.node(run, "IBD-N81")
    run.check(
        "CRP criterion: If met -> UC Tier 3",
        [t["nodeId"] for t in detail["leadsTo"]] == ["IBD-N42"],
        detail["leadsTo"],
    )
    unmet = api.stream(
        run,
        "record day-3 CRP 20",
        {"mode": "review", "branchNodeId": "IBD-N81", "reviewValue": "20"},
    )
    rev = of(unmet, "reviewed")
    run.check(
        "CRP 20 does not meet; no new walk",
        bool(rev)
        and rev[0]["met"] is False
        and "does not meet" in rev[0]["text"]
        and not of(unmet, "done"),
        rev,
    )
    met = api.stream(
        run,
        "record day-3 CRP 60",
        {"mode": "review", "branchNodeId": "IBD-N81", "reviewValue": "60"},
    )
    run.check("CRP 60 meets", bool(of(met, "reviewed")) and of(met, "reviewed")[0]["met"])
    walk_ok(run, met)
    entry_has(api, run, "UC Tier 3")
    for bad in ("nan", "-5", "abc"):
        ev = api.stream(
            run,
            f"record day-3 {bad}",
            {"mode": "review", "branchNodeId": "IBD-N81", "reviewValue": bad},
        )
        errs = of(ev, "error")
        run.check(f"{bad} refused", bool(errs) and errs[0].get("code") == "invalid_request", errs)
    toxic = api.node(run, "IBD-N90")
    run.check(
        "Toxic megacolon leads to colectomy triggers",
        [t["nodeId"] for t in toxic["nextPaths"]] == ["IBD-N96"],
        toxic["nextPaths"],
    )


def t03(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    fu = api.stream(
        run,
        "follow-up: Remicade failed",
        {
            "mode": "follow_up",
            "text": "Remicade failed. steroids work. Suggest alternate treatment plan",
        },
    )
    notes = of(fu, "history")
    run.check(
        "history maps Remicade to infliximab",
        bool(notes) and "infliximab" in notes[0]["text"].lower(),
        notes and notes[0]["text"],
    )
    walk_ok(run, fu)
    status = api.map_status(run)
    run.check("Infliximab shows Tried", status.get("IBD-N53") == "tried", status.get("IBD-N53"))
    entry_has(api, run, "after anti-TNF failure")
    rev = api.stream(
        run,
        "record day-3 CRP 60",
        {"mode": "review", "branchNodeId": "IBD-N81", "reviewValue": "60"},
    )
    walk_ok(run, rev)
    status = api.map_status(run)
    run.check(
        "after the review infliximab is still Tried",
        status.get("IBD-N53") == "tried",
        status.get("IBD-N53"),
    )
    lines = [p["text"] for p in of(rev, "line")]
    run.check(
        "no infliximab line after the review", not any("infliximab" in t.lower() for t in lines)
    )


def t04(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    fu = api.stream(
        run,
        "follow-up: refractory",
        {"mode": "follow_up", "text": "Infliximab stopped working and steroids did not work"},
    )
    walk_ok(run, fu)
    cited = {n for p in of(fu, "line") for n in p["nodeIds"]}
    run.check(
        "steroid-refractory surgical review cited (IBD-N99)", "IBD-N99" in cited, sorted(cited)
    )


def t05(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    resp = api.call(
        run,
        "edit Methylprednisolone dose to 40 mg",
        "POST",
        f"/api/cases/{run.case_id}/treatment-edits",
        {"nodeId": "IBD-N52", "newValues": {"doseValue": 40}},
    )
    run.check("edit accepted", resp.status_code == 201, resp.status_code)
    edited = api.node(run, "IBD-N52").get("edited")
    run.check("node detail shows the stored edit (edited marker)", bool(edited), edited)


def t06(api: Api, run: Run, text: str) -> None:
    events = start(api, run, text, UC)
    walk_ok(run, events)
    walk_id = done_of(events).get("walkId")
    ex = api.stream(
        run,
        "explore infectious colitis",
        {"mode": "explore", "walkId": walk_id, "branchNodeId": "IBD-N13"},
    )
    run.check("explore lane opens without errors", not of(ex, "error"), of(ex, "error"))
    stop = api.stream(
        run,
        "stop exploring",
        {"mode": "stop_explore", "walkId": walk_id, "branchNodeId": "IBD-N13"},
    )
    run.check("lane closes", bool(of(stop, "lane_closed")), [n for n, _ in stop])
    entry_has(api, run, "UC Tier 2")


def t07(api: Api, run: Run, text: str) -> None:
    first = api.stream(run, "start walk", {"mode": "start", "text": text})
    forms = of(first, "form")
    hb = [
        f
        for f in (forms[0]["fields"] if forms else [])
        if "h" in str(f.get("name", "")).lower()[:2]
    ]
    run.check(
        "Hb chip converted to 10.2 g/dL",
        any(
            str(f.get("value")) in ("10.2", "10.20") and str(f.get("unit")).lower() == "g/dl"
            for f in hb
        ),
        hb,
    )

    def invalid(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [dict(f, value="abc") if f in hb_findings else f for f in found]

    hb_findings = (
        [f for f in findings_from(forms[0]) if f.get("name") in {h.get("name") for h in hb}]
        if forms
        else []
    )
    bad = (
        api.stream(
            run,
            "confirm with Hb = abc",
            {
                "mode": "continue",
                "walkId": forms[0]["walkId"],
                "formMessageId": forms[0]["messageId"],
                "formValues": {"findings": invalid(findings_from(forms[0]))},
            },
        )
        if forms
        else []
    )
    run.check(
        "invalid Hb keeps the walk from starting",
        bool(of(bad, "form") or of(bad, "error")) and not of(bad, "line"),
        [n for n, _ in bad],
    )
    events = walk_through(api, run, bad, UC)
    resp = api.call(
        run,
        "chat during the walk: she's 62 kg, also joint pain",
        "POST",
        f"/api/cases/{run.case_id}/messages",
        {"text": "she's 62 kg, also joint pain for 2 months"},
    )
    run.check(
        "chat offers Review findings and re-walk",
        resp.status_code == 201 and bool(resp.json().get("offers")),
        resp.json(),
    )
    patch = api.call(
        run,
        "set weight 62 kg on the card",
        "PATCH",
        f"/api/cases/{run.case_id}/patient",
        {"weightKg": 62},
    )
    run.check("card weight is 62 kg", patch.json().get("patient", {}).get("weightKg") == 62)
    walk_ok(run, events)


def t08(api: Api, run: Run, text: str) -> None:
    events = start(api, run, text, {"IBD-N20": "negative"})
    walk_ok(run, events, "needs_data")
    status = api.map_status(run)
    run.check(
        "colonoscopy still ? not yet tested",
        status.get("IBD-N21") == "test_needed",
        status.get("IBD-N21"),
    )


def simple(entry: str, answers: dict[str, str], outcome: str = "answered") -> Callable[..., None]:
    def play(api: Api, run: Run, text: str) -> None:
        walk_ok(run, start(api, run, text, answers), outcome)
        if entry:
            entry_has(api, run, entry)

    return play


def t12(api: Api, run: Run, text: str) -> None:
    walk_ok(
        run,
        start(
            api,
            run,
            text,
            {
                "IBD-N20": "negative",
                "IBD-N21": "crohn's disease",
                "IBD-N24": "L2",
                "IBD-N25": "B1",
                "IBD-N26": "moderate",
            },
        ),
    )
    entry_has(api, run, "Crohn's Tier 2")
    before = api.node(run, "IBD-N53").get("dose")
    run.check("no weight: dose asks for the weight", "weight" in json.dumps(before).lower(), before)
    api.call(
        run, "set weight 62 kg", "PATCH", f"/api/cases/{run.case_id}/patient", {"weightKg": 62}
    )
    after = api.node(run, "IBD-N53").get("dose")
    run.check("62 kg: 310 mg", "310" in json.dumps(after), after)


def t14(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    safety = {s["check"]: s["status"] for s in api.node(run, "IBD-N51")["safety"]}
    run.check("allergy ok against the penicillin node", safety.get("allergy") == "ok", safety)
    run.check("pregnancy not checked", safety.get("pregnancy") == "not_checked", safety)
    run.check(
        "duplicate class conflict (methylprednisolone on card)",
        safety.get("duplicate_class") == "conflict",
        safety,
    )


def t16(api: Api, run: Run, text: str) -> None:
    view = api.get(f"/api/cases/{run.case_id}")
    run.check(
        "banner: newer version available", bool(view.get("newerVersion")), view.get("newerVersion")
    )
    done = walk_ok(run, start(api, run, text, UC))
    run.check(
        "walked on IBD 1.0",
        str(done.get("packVersion", "")).endswith("1.0"),
        done.get("packVersion"),
    )
    fu = api.stream(
        run, "follow-up on 1.0", {"mode": "follow_up", "text": "Remicade failed. steroids work."}
    )
    walk_ok(run, fu, "out_of_knowledge")
    rew = api.stream(run, "re-walk on the newer version", {"mode": "rewalk"})
    rew = walk_through(api, run, rew, UC)
    done = walk_ok(run, rew)
    run.check(
        "re-walk is on IBD 1.2",
        str(done.get("packVersion", "")).endswith("1.2"),
        done.get("packVersion"),
    )
    fu = api.stream(
        run, "follow-up on 1.2", {"mode": "follow_up", "text": "Remicade failed. steroids work."}
    )
    walk_ok(run, fu)
    entry_has(api, run, "after anti-TNF failure")


def t17(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    walk_ok(
        run,
        api.stream(
            run,
            "follow-up: Remicade failed",
            {"mode": "follow_up", "text": "Remicade failed. steroids work."},
        ),
    )
    chosen = api.call(
        run,
        "choose Vedolizumab",
        "POST",
        f"/api/cases/{run.case_id}/traverse",
        {"nodeId": "IBD-N57"},
    )
    run.check("choice recorded", chosen.status_code == 201, chosen.status_code)
    status = api.map_status(run)
    run.check(
        "both screens To do first",
        status.get("IBD-N110") == "todo_first" and status.get("IBD-N111") == "todo_first",
        (status.get("IBD-N110"), status.get("IBD-N111")),
    )
    event = api.call(
        run,
        "TB screen negative",
        "POST",
        f"/api/cases/{run.case_id}/events",
        {"kind": "result", "nodeId": "IBD-N110", "value": "negative"},
    )
    run.check("result recorded", event.status_code == 201, event.status_code)
    status = api.map_status(run)
    run.check("TB screen Done", status.get("IBD-N110") == "done", status.get("IBD-N110"))
    card = api.call(
        run,
        "cited card for the lit nodes",
        "POST",
        f"/api/cases/{run.case_id}/events/card",
        {"nodeIds": ["IBD-N111"]},
    )
    body = card.json() if card.status_code == 200 else {}
    run.check(
        "card lines are grounded (0 rejected)",
        card.status_code == 200 and body.get("rejected", 1) == 0,
        body,
    )
    api.call(
        run,
        "choose Ustekinumab",
        "POST",
        f"/api/cases/{run.case_id}/traverse",
        {"nodeId": "IBD-N54"},
    )
    status = api.map_status(run)
    run.check("screens asked again", status.get("IBD-N110") == "todo_first", status.get("IBD-N110"))


def t18(api: Api, run: Run, text: str) -> None:
    walk_ok(run, start(api, run, text, UC))
    api.call(
        run,
        "choose Hydrocortisone",
        "POST",
        f"/api/cases/{run.case_id}/traverse",
        {"nodeId": "IBD-N51"},
    )
    status = api.map_status(run)
    run.check(
        "CRP monitoring is Due, not Suggested",
        status.get("IBD-N71") == "due",
        status.get("IBD-N71"),
    )
    api.call(
        run,
        "toxic megacolon present",
        "POST",
        f"/api/cases/{run.case_id}/events",
        {"kind": "present", "nodeId": "IBD-N90"},
    )
    status = api.map_status(run)
    run.check(
        "megacolon Present, colectomy Now",
        status.get("IBD-N90") == "present" and status.get("IBD-N96") == "now",
        (status.get("IBD-N90"), status.get("IBD-N96")),
    )
    api.call(
        run,
        "new bloody diarrhoea present",
        "POST",
        f"/api/cases/{run.case_id}/events",
        {"kind": "present", "nodeId": "IBD-N94"},
    )
    status = api.map_status(run)
    run.check("stool culture Due again", status.get("IBD-N20") == "due", status.get("IBD-N20"))
    api.call(
        run,
        "stool culture negative",
        "POST",
        f"/api/cases/{run.case_id}/events",
        {"kind": "result", "nodeId": "IBD-N20", "value": "negative"},
    )
    status = api.map_status(run)
    run.check("stool culture Done", status.get("IBD-N20") == "done", status.get("IBD-N20"))


PLAYS: dict[str, Callable[..., None]] = {
    "T01": t01,
    "T02": t02,
    "T03": t03,
    "T04": t04,
    "T05": t05,
    "T06": t06,
    "T07": t07,
    "T08": t08,
    "T09": simple(
        "UC Tier 1",
        {
            "IBD-N20": "negative",
            "IBD-N21": "ulcerative colitis",
            "IBD-N22": "E1",
            "IBD-N23": "mild",
        },
    ),
    "T10": simple("UC Tier 2", UC),
    "T11": simple(
        "Crohn's Tier 1",
        {
            "IBD-N20": "negative",
            "IBD-N21": "crohn's disease",
            "IBD-N24": "L1",
            "IBD-N25": "B1",
            "IBD-N26": "mild",
        },
    ),
    "T12": t12,
    "T13": simple(
        "Crohn's Tier 2",
        {
            "IBD-N20": "negative",
            "IBD-N21": "crohn's disease",
            "IBD-N24": "L3",
            "IBD-N25": "B3",
            "IBD-N26": "severe",
        },
    ),
    "T14": t14,
    "T15": simple("", {}, "out_of_knowledge"),
    "T16": t16,
    "T17": t17,
    "T18": t18,
    "U01": simple("Tier 1", {"URO-N3": "ureteric stone"}),
    "U02": simple("", {"URO-N3": "ureteric stone"}),
}


def load_cases() -> list[Any]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import seed_test_cases

    return list(seed_test_cases.CASES)


def find_case_ids(api: Api, profile: str) -> dict[str, str]:
    api.sign_in(profile)
    results = api.get("/api/patients", q="").get("results", [])
    ids: dict[str, str] = {}
    for r in results:
        detail = api.get(f"/api/cases/{r['caseId']}")
        name = str(detail["patient"]["syntheticName"])
        ids[name.split(" ")[0]] = r["caseId"]
    return ids


def report_md(runs: list[Run], model: str) -> str:
    passed = sum(c["pass"] for r in runs for c in r.checks)
    total = sum(len(r.checks) for r in runs)
    out = [
        "# Live test cases",
        "",
        f"Model: `{model}`. Checks passed: **{passed} / {total}**. Synthetic cases only; "
        "decision support, not diagnosis.",
        "",
        "| Case | Checks | Time | Ungrounded | Notes |",
        "|---|---|---|---|---|",
    ]
    for r in runs:
        ok = sum(c["pass"] for c in r.checks)
        secs = sum(s.get("seconds", 0) for s in r.steps)
        ungrounded = [
            s["done"]["counts"].get("ungrounded")
            for s in r.steps
            if s.get("done") and s["done"].get("counts")
        ]
        fails = "; ".join(c["check"] for c in r.checks if not c["pass"])
        out.append(
            f"| {r.tid} | {ok}/{len(r.checks)} | {secs:.0f}s | {ungrounded} | "
            f"{r.error or fails or 'ok'} |"
        )
    for r in runs:
        out += ["", f"## {r.tid} · {r.case_id}", ""]
        for c in r.checks:
            mark = "✓" if c["pass"] else "✗"
            got = "" if c["pass"] else f" — got `{json.dumps(c['got'], ensure_ascii=False)[:200]}`"
            out.append(f"- {mark} {c['check']}{got}")
        if r.error:
            out.append(f"- ✗ stopped: {r.error}")
        out += ["", "| Step | Time | Events | Drawn by |", "|---|---|---|---|"]
        for s in r.steps:
            ev = (
                ", ".join(f"{k}×{v}" for k, v in s.get("events", {}).items())
                or f"HTTP {s.get('http')}"
            )
            out.append(
                f"| {s['action']} | {s.get('seconds', 0)}s | {ev} | "
                f"{'; '.join(s.get('components', []))} |"
            )
        chips = next(
            (
                s["forms"][0]["fields"]
                for s in r.steps
                if s.get("forms") and s["forms"][0]["kind"] == "confirm-findings"
            ),
            None,
        )
        if chips:
            out += [
                "",
                "Extracted chips: "
                + "; ".join(
                    " ".join(
                        str(f.get(k)) for k in ("name", "value", "unit", "duration") if f.get(k)
                    )
                    for f in chips
                ),
            ]
        notices = [n for s in r.steps for n in s.get("notices", []) if n]
        if notices:
            out += [""] + [f"> {n}" for n in notices]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    wanted = set(argv)
    client = httpx.Client(base_url=BASE, timeout=900.0)
    health = client.get("/api/health").json()
    log(f"health: {health}")
    api = Api(client)
    cases = [c for c in load_cases() if not wanted or c.tid in wanted]
    ids = {**find_case_ids(api, "p-urologist"), **find_case_ids(api, "p-maya")}
    runs: list[Run] = []
    current = "p-maya"
    for case in cases:
        if case.tid not in ids:
            log(f"{case.tid}: not found — run scripts/seed_test_cases.py first")
            continue
        if case.owner != current:
            api.sign_in(case.owner)
            current = case.owner
        run = Run(case.tid, ids[case.tid])
        log(f"=== {case.tid} {case.title} ({run.case_id})")
        client.post(f"/api/cases/{run.case_id}/lock", json={"tabId": TAB})
        try:
            PLAYS[case.tid](api, run, case.start)
        except Exception as exc:  # record and move on to the next case
            run.error = f"{type(exc).__name__}: {exc}"[:400]
            log(f"  STOPPED {run.error}")
        runs.append(run)
        client.request("DELETE", f"/api/cases/{run.case_id}/lock", json={"tabId": TAB})
        OUT_JSON.write_text(json.dumps([r.__dict__ for r in runs], ensure_ascii=False, indent=1))
        OUT_MD.write_text(report_md(runs, str(health.get("model", health))), encoding="utf-8")
    failed = [r.tid for r in runs if r.error or not all(c["pass"] for c in r.checks)]
    log(f"done: {len(runs)} cases, failing: {failed or 'none'}; report {OUT_MD.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
