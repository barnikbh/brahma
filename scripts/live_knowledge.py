"""Live knowledge-update rehearsal: conversation, real-URL draft, reviewer publish.

Run from the repository root against a running server (default base
http://127.0.0.1:8000, override with BRAHMA_REHEARSAL_BASE)::

    .venv/bin/python scripts/live_knowledge.py

As Dr. Maya: sends a vague update request (expects clarifying questions), then a
tofacitinib safety update citing the FDA JAK-warning page (fda.gov blocks the
fetcher's user agent, so a graceful "could not read" reply is expected), then
the same update from the tofacitinib Wikipedia page (expects a drafted
proposal). As the reviewer: publishes the proposal and confirms the new live
version. Finally replays the impossible new-pack request (expects one ask round,
then an early stop — never repeated questions). Exit code 0 means everything
behaved, 2 means it degraded gracefully (asked only, or publish blocked),
1 means a crash, an HTTP 500 or a wrong turn status.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import httpx

BASE = os.environ.get("BRAHMA_REHEARSAL_BASE", "http://127.0.0.1:8000")
FDA_JAK_URL = (
    "https://www.fda.gov/drugs/drug-safety-and-availability/"
    "fda-requires-warnings-about-increased-risk-serious-heart-related-events-cancer-blood-clots-and-death"
)
WIKI_TOFACITINIB_URL = "https://en.wikipedia.org/wiki/Tofacitinib"
WIKI_FOLLOW_UP = (
    "Use node IBD-N58. Draft whatever boxed-warning safety content the page states "
    "for tofacitinib, paraphrased into the node's safety text. Keep all existing "
    "dose information unchanged. If the page states no boxed warning, say so."
)
NEWPACK_ASK = (
    "Create knowledge on lung cancer. Treatment plan based on mutation. For example "
    "for PDL1 gene, immunotherapy is done. Give this a different ID outside of IBD "
    "and URO."
)
NEWPACK_REFUSE = "1. yes new, 2. find your own sources, 3. find it all. do your research"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[+{time.time() - T0:7.1f}s] {msg}", flush=True)


def show_thread(tag: str, body: dict[str, Any]) -> None:
    log(f"{tag} status={body.get('status')} rounds={body.get('rounds')}")
    for message in body.get("messages", []):
        text = str(message.get("text", ""))[:300]
        log(f"{tag} [{message.get('role')}] proposal={message.get('proposalId')} :: {text!r}")
    for proposal in body.get("proposals", []):
        log(
            f"{tag} proposal={proposal.get('proposalId')} origin={proposal.get('origin')} "
            f"copyFlagged={proposal.get('copyFlaggedNodeIds')}"
        )
        for change in proposal.get("changes", [])[:4]:
            log(
                f"{tag}   change node={change.get('nodeId')} url={change.get('sourceUrl')} "
                f"passage={(change.get('sourcePassage') or '')[:120]!r}"
            )


def main() -> int:
    doctor = httpx.Client(base_url=BASE, timeout=900.0)
    assert doctor.post("/api/session", json={"profileId": "p-maya"}).status_code == 200
    assert doctor.post("/api/disclaimer").status_code == 200

    log("vague request (expect clarifying questions)...")
    vague = doctor.post(
        "/api/knowledge/updates", json={"text": "Update ustekinumab maintenance dose"}
    )
    log(f"vague -> HTTP {vague.status_code}")
    if vague.status_code >= 500:
        log(f"SERVER ERROR: {vague.text[:300]}")
        return 1
    show_thread("VAGUE", vague.json())

    log("FDA URL request (expect a graceful could-not-read reply)...")
    fda_text = f"Update the tofacitinib safety warning from {FDA_JAK_URL}"
    fda = doctor.post("/api/knowledge/updates", json={"text": fda_text})
    log(f"fda -> HTTP {fda.status_code}")
    if fda.status_code >= 500:
        log(f"SERVER ERROR: {fda.text[:300]}")
        return 1
    show_thread("FDA", fda.json())

    log("Wikipedia URL request (expect a drafted proposal)...")
    wiki_text = f"Update the tofacitinib safety information from {WIKI_TOFACITINIB_URL}"
    drafted = doctor.post("/api/knowledge/updates", json={"text": wiki_text})
    log(f"wiki -> HTTP {drafted.status_code}")
    if drafted.status_code >= 500:
        log(f"SERVER ERROR: {drafted.text[:300]}")
        return 1
    if drafted.status_code != 200:
        log(f"GRACEFUL: {drafted.text[:300]}")
        return 2
    url_body = drafted.json()
    show_thread("WIKI", url_body)
    if url_body.get("status") != "proposed":
        thread_id = url_body.get("threadId")
        log(f"WIKI follow-up in thread {thread_id}...")
        follow = doctor.post(
            "/api/knowledge/updates", json={"text": WIKI_FOLLOW_UP, "threadId": thread_id}
        )
        log(f"wiki-follow-up -> HTTP {follow.status_code}")
        if follow.status_code >= 500:
            log(f"SERVER ERROR: {follow.text[:300]}")
            return 1
        if follow.status_code != 200:
            log(f"GRACEFUL: {follow.text[:300]}")
            return 2
        url_body = follow.json()
        show_thread("WIKI2", url_body)
    proposals = url_body.get("proposals", [])
    if url_body.get("status") != "proposed" or not proposals:
        log("GRACEFUL: assistant asked instead of drafting")
        return 2
    proposal_id = proposals[0]["proposalId"]
    detail = doctor.get(f"/api/knowledge/proposals/{proposal_id}")
    log(f"proposal detail -> HTTP {detail.status_code}")
    if detail.status_code != 200:
        log(f"GRACEFUL: {detail.text[:300]}")
        return 2

    reviewer = httpx.Client(base_url=BASE, timeout=300.0)
    assert reviewer.post("/api/session", json={"profileId": "p-reviewer"}).status_code == 200
    assert reviewer.post("/api/disclaimer").status_code == 200
    log(f"publishing {proposal_id} as reviewer...")
    published = reviewer.post(
        f"/api/knowledge/proposals/{proposal_id}/publish", json={"comment": "Live rehearsal check"}
    )
    log(f"publish -> HTTP {published.status_code}")
    if published.status_code >= 500:
        log(f"SERVER ERROR: {published.text[:300]}")
        return 1
    if published.status_code != 200:
        log(f"GRACEFUL: publish refused: {published.text[:300]}")
        return 2
    versions = reviewer.get("/api/knowledge/versions", params={"pack": "IBD"}).json()["versions"]
    live = [v for v in versions if v.get("status") == "live"]
    log(f"VERSIONS: {[(v.get('version'), v.get('status')) for v in versions[:4]]}")
    if not live or live[0].get("version") == "1.1":
        log("GRACEFUL: no new live version")
        return 2
    log(f"FULL LOOP OK: published -> live IBD {live[0].get('version')}")

    log("Impossible request (expect ask, then early stop)...")
    first = doctor.post("/api/knowledge/updates", json={"text": NEWPACK_ASK})
    if first.status_code != 200:
        log(f"FAIL: new-pack ask -> HTTP {first.status_code}: {first.text[:200]}")
        return 1
    first_body = first.json()
    show_thread("NEWPACK1", first_body)
    if first_body.get("status") != "open":
        log(f"FAIL: expected open, got {first_body.get('status')}")
        return 1
    second = doctor.post(
        "/api/knowledge/updates",
        json={"text": NEWPACK_REFUSE, "threadId": first_body.get("threadId")},
    )
    if second.status_code != 200:
        log(f"FAIL: new-pack refuse -> HTTP {second.status_code}: {second.text[:200]}")
        return 1
    second_body = second.json()
    show_thread("NEWPACK2", second_body)
    last_text = str(second_body.get("messages", [])[-1].get("text", ""))
    if second_body.get("status") != "stuck" or "instead of asking again" not in last_text:
        log("FAIL: expected early stop with the explanatory message")
        return 1
    log("NEWPACK OK: asked once, then stopped with an explanation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
