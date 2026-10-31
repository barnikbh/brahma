"""Scripted demo walk against a running server, for live-model rehearsal.

Run from the repository root against your own server (it must already run on the
base URL, default http://127.0.0.1:8000)::

    .venv/bin/python scripts/live_walk.py
    BRAHMA_REHEARSAL_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/live_walk.py

Signs in as Dr. Maya, creates one synthetic patient, walks the IBD demo case
(requesting the same needs-data answers as the recorded demo), runs the
anti-TNF-failure follow-up turn and prints every emitted line. Exit code 0 means
the walk and the follow-up both answered with 0 ungrounded lines, 2 means one of
them had some ungrounded, 1 means something did not finish.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import httpx

BASE = os.environ.get("BRAHMA_REHEARSAL_BASE", "http://127.0.0.1:8000")
TAB = "tab-live-1"
HEADERS = {"X-Brahma-Tab": TAB}
DEMO_TEXT = "34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g"
ANSWERS = {
    "IBD-N20": "negative",
    "IBD-N21": "ulcerative colitis",
    "IBD-N22": "E3",
    "IBD-N23": "severe",
}
FOLLOW_UP_TEXT = "Remicade failed. steroids work. Suggest alternate treatment plan"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[+{time.time() - T0:7.1f}s] {msg}", flush=True)


def walk_events(
    client: httpx.Client, case_id: str, body: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    event, data = "", ""
    with client.stream("POST", f"/api/cases/{case_id}/walk", json=body, headers=HEADERS) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"walk HTTP {resp.status_code}: {resp.read().decode()[:500]}")
        for raw in resp.iter_lines():
            line = raw.strip()
            if not line:
                if event:
                    payload: dict[str, Any] = json.loads(data or "{}")
                    events.append((event, payload))
                    log(f"  <- {event}: {summarize(event, payload)}")
                    event, data = "", ""
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = line.split(":", 1)[1].strip()
    return events


def summarize(name: str, payload: dict[str, Any]) -> str:
    if name == "progress":
        return str(payload.get("step"))
    if name == "form":
        fields = payload.get("fields", [])
        names = [f.get("name", f.get("nodeId", "?")) for f in fields]
        return f"kind={payload.get('kind')} fields={names}"
    if name == "line":
        text = str(payload.get("text", ""))[:100]
        return f"nodes={payload.get('nodeIds')} {text!r}"
    if name == "done":
        return f"outcome={payload.get('outcome')} counts={payload.get('counts')}"
    if name == "error":
        return json.dumps(payload)[:300]
    if name == "paused":
        return f"waitingFor={payload.get('waitingFor')}"
    return json.dumps(payload)[:160]


def payloads(events: list[tuple[str, dict[str, Any]]], kind: str) -> list[dict[str, Any]]:
    return [data for name, data in events if name == kind]


DEMO_PATIENT = {
    "syntheticName": "Live Demo Patient (synthetic)",
    "age": 34,
    "sex": "female",
    "weightKg": 58,
}


def run_case_walk(
    client: httpx.Client, patient: dict[str, Any], text: str, answers: dict[str, str]
) -> dict[str, Any]:
    """Drive one full walk: patient, findings confirm, needs-data rounds to done.

    Returns {"ok": True, "caseId", "lines", "done", "extracted"} or {"ok": False,
    "reason"}. Shared with the benchmark runner.
    """
    created = client.post("/api/patients", json=patient)
    assert created.status_code == 201, created.text
    case_id: str = created.json()["case"]["caseId"]
    log(f"case {case_id}")
    assert client.post(f"/api/cases/{case_id}/lock", json={"tabId": TAB}).json() == {
        "state": "held"
    }

    log("walk start...")
    events = walk_events(client, case_id, {"mode": "start", "text": text})
    forms = payloads(events, "form")
    if not forms or payloads(events, "error"):
        log("START DID NOT REACH CONFIRM-FINDINGS; stopping")
        return {"ok": False, "reason": "no-confirm-form"}
    form = forms[0]
    log(f"confirm-findings fields: {json.dumps(form['fields'])[:600]}")
    findings = [
        {
            "kind": f["findingKind"],
            "name": f["name"],
            "value": f["value"],
            "unit": f["unit"],
            "duration": f["duration"],
        }
        for f in form["fields"]
    ]
    walk_id = form["walkId"]
    step = walk_events(
        client,
        case_id,
        {
            "mode": "continue",
            "walkId": walk_id,
            "formMessageId": form["messageId"],
            "formValues": {"findings": findings},
        },
    )
    events += step
    for round_no in range(1, 7):
        needs = payloads(step, "form")
        dones = payloads(step, "done")
        if dones or payloads(step, "error"):
            break
        if not needs:
            log(f"round {round_no}: no form and no done; stopping")
            return {"ok": False, "reason": "no-form-no-done"}
        need = needs[-1]
        fields = need.get("fields", [])
        unknown = [
            f for f in fields if f.get("nodeId") not in answers and f.get("name") not in answers
        ]
        if unknown:
            log(f"UNEXPECTED needs-data fields: {json.dumps(fields)[:500]}; stopping")
            return {"ok": False, "reason": "unexpected-needs"}

        def key(f: dict[str, Any]) -> str:
            return str(f.get("nodeId") or f.get("name"))

        chosen = {key(f): answers[key(f)] for f in fields}
        log(f"round {round_no}: answering {chosen}")
        step = walk_events(
            client,
            case_id,
            {
                "mode": "continue",
                "walkId": walk_id,
                "formMessageId": need["messageId"],
                "formValues": chosen,
            },
        )
        events += step
    else:
        log("too many form rounds; stopping")
        return {"ok": False, "reason": "too-many-rounds"}

    dones = payloads(events, "done")
    errors = payloads(events, "error")
    lines = payloads(events, "line")
    log(f"TOTAL lines={len(lines)} done={bool(dones)} errors={len(errors)}")
    if not dones:
        log(f"NO DONE. errors={errors}")
        return {"ok": False, "reason": "no-done", "errors": errors}
    return {"ok": True, "caseId": case_id, "lines": lines, "done": dones[0], "extracted": findings}


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=900.0)
    log(f"health: {client.get('/api/health').json()}")
    assert client.post("/api/session", json={"profileId": "p-maya"}).status_code == 200
    assert client.post("/api/disclaimer").status_code == 200
    log("signed in as p-maya, disclaimer accepted")
    result = run_case_walk(client, DEMO_PATIENT, DEMO_TEXT, ANSWERS)
    if not result["ok"]:
        return 1
    case_id = result["caseId"]
    lines = result["lines"]
    d = result["done"]
    outcome = d.get("outcome")
    counts = d.get("counts")
    pack = d.get("packVersion")
    log(f"RESULT outcome={outcome} counts={counts} pack={pack}")
    for line in lines:
        print(f"  LINE nodes={line.get('nodeIds')} :: {line.get('text')}")
    walk_code = 0 if d.get("counts", {}).get("ungrounded", 99) == 0 else 2

    log(f"follow-up: {FOLLOW_UP_TEXT!r}")
    follow = walk_events(client, case_id, {"mode": "follow_up", "text": FOLLOW_UP_TEXT})
    histories = payloads(follow, "history")
    follow_done = payloads(follow, "done")
    follow_lines = payloads(follow, "line")
    follow_errors = payloads(follow, "error")
    log(f"FOLLOW-UP lines={len(follow_lines)} done={bool(follow_done)} errors={len(follow_errors)}")
    if histories:
        log(f"FOLLOW-UP history: {histories[0].get('text', '')[:200]}")
    if not follow_done:
        log(f"FOLLOW-UP NO DONE. errors={follow_errors}")
        return 1
    fd = follow_done[0]
    log(f"FOLLOW-UP RESULT outcome={fd.get('outcome')} counts={fd.get('counts')}")
    for line in follow_lines:
        print(f"  FU-LINE nodes={line.get('nodeIds')} :: {line.get('text')}")
    cited = {n for line in follow_lines for n in line.get("nodeIds", [])}
    log(f"FOLLOW-UP cited: {sorted(cited)}")
    view = client.get(f"/api/cases/{case_id}").json()
    history = (view["messages"][-1].get("body") or {}).get("history")
    log(f"FOLLOW-UP stored history: {json.dumps(history)[:200]}")
    follow_code = 0 if fd.get("counts", {}).get("ungrounded", 99) == 0 else 2
    return max(walk_code, follow_code)


if __name__ == "__main__":
    sys.exit(main())
