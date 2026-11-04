"""Reset the local database and seed synthetic test patients for every feature.

Run from the repository root with the server STOPPED (it holds the database open)::

    .venv/bin/python scripts/seed_test_cases.py

What it does:

1. Deletes the old database (``BRAHMA_DB_PATH``, default ``data/brahma.db``, with its
   ``-wal``/``-shm`` files), the walk log and the leftover ``data/manual.*`` and
   ``data/u4-smoke.*`` scratch databases. Old cases are not migrated.
2. Creates a fresh database: the archived IBD 1.0 pack (``scripts/seed_data/``), then
   the live packs in ``content/`` (IBD 1.2 and urology 0.1), then the demo profiles.
3. Creates one synthetic patient per test case below. Each chat starts with a short
   note naming the test and what to type first. Steps and expected results for every
   case are in ``docs/test-cases.md``; regenerate it with ``--guide`` after editing
   ``CASES``.

Every patient is synthetic (NFR6.1): invented names, no real records.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from brahma.agent.db import ag_connect  # noqa: E402
from brahma.cases import MessageIn, NewPatient  # noqa: E402
from brahma.cases.service import CaseService  # noqa: E402
from brahma.knowledge.db import kg_connect  # noqa: E402
from brahma.knowledge.models import PackVersionRef  # noqa: E402
from brahma.knowledge.service import KnowledgeService  # noqa: E402
from brahma.platform.db import DEFAULT_DB_PATH  # noqa: E402
from brahma.platform.profiles import ProfileRepository  # noqa: E402
from brahma.server.services import load_initial_packs  # noqa: E402
from brahma.updates.db import ensure_up_schema  # noqa: E402

ARCHIVED_PACKS = (ROOT / "scripts" / "seed_data" / "ibd-1.0.yaml",)
GUIDE = ROOT / "docs" / "test-cases.md"
MAYA, UROLOGIST = "p-maya", "p-urologist"
DEMO_TEXT = "34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g"
DEMO_TESTS = (
    "Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; "
    "then extent **E3**, severity **severe**."
)


@dataclass(frozen=True)
class TestCase:
    """One seeded patient: who owns it, the card, what to type and what should happen."""

    tid: str
    title: str
    covers: str
    patient: NewPatient
    start: str
    steps: list[str]
    expect: list[str]
    owner: str = MAYA
    pin: str | None = None  # "IBD@1.0" pins the case to the archived version


def _patient(name: str, age: int, sex: str, weight: float | None, **extra: object) -> NewPatient:
    return NewPatient.model_validate(
        {
            "syntheticName": f"{name} (synthetic)",
            "age": age,
            "sex": sex,
            "weightKg": weight,
            **extra,
        }
    )


CASES: list[TestCase] = [
    TestCase(
        "T01",
        "Demo walk: acute severe UC",
        "US3.1-US3.5, US4.1, US7.1, AC3.2.1, AC3.2.2",
        _patient("T01 Asha Demo", 34, "female", 58),
        DEMO_TEXT,
        [
            "Type the start text and confirm the findings.",
            DEMO_TESTS,
            "Click a cited line, then its node on the map; open Hydrocortisone.",
            "Press Choose this option.",
            "Open the why panel.",
        ],
        [
            "Map lights up column by column; tests show ? until answered.",
            "Pathway reaches ulcerative colitis, pancolitis, severe, with Tier 2 IV steroids "
            "as Start here.",
            "Summary shows 0 ungrounded (1 is possible on the live model), the pack IBD 1.2 "
            "and the model.",
            "Tier 2 drugs are grey Options; choosing one marks it Chosen, lights its "
            "monitoring blue and shows the Now on card.",
            "Every why sentence has node chips.",
        ],
    ),
    TestCase(
        "T02",
        "Day-3 review: unmet, then met",
        "Day-3 review (Nov 4), criterion If met links",
        _patient("T02 Bina Review", 34, "female", 60),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Open the monitor node Day 3 on IV steroids: CRP above 45 mg/L.",
            "Record 20.",
            "Record 60.",
            "Try nan, -5 and abc.",
            "Open Toxic megacolon.",
        ],
        [
            "The criterion panel shows If met -> UC Tier 3.",
            "20: says the value does not meet the criterion and the plan is unchanged; "
            "no new walk.",
            "60: a new review walk; UC Tier 3 becomes Start here; still 0 ungrounded.",
            "nan, -5 and abc are refused with an error; nothing is recorded.",
            "Toxic megacolon shows Where it leads: Emergency colectomy triggers.",
        ],
    ),
    TestCase(
        "T03",
        "Follow-up after anti-TNF failure, then day-3 review",
        "Follow-up turn, US3.2 history, today's review fix",
        _patient("T03 Carmen Followup", 34, "female", 64),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Type: Remicade failed. steroids work. Suggest alternate treatment plan (press Enter).",
            "Then record day-3 CRP 60 on the CRP criterion.",
        ],
        [
            "Brahma notes the history (Remicade mapped to infliximab).",
            "The plan moves to UC after anti-TNF failure; Infliximab shows Tried.",
            "After the CRP 60 review, infliximab is still Tried and never suggested again.",
        ],
    ),
    TestCase(
        "T04",
        "Steroid-refractory follow-up",
        "Follow-up turn, surgical escalation",
        _patient("T04 Divya Refractory", 34, "female", 66),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Type: Infliximab stopped working and steroids did not work",
        ],
        [
            "History reads infliximab lost response; corticosteroid no response.",
            "Watch-outs include the steroid-refractory surgical review.",
        ],
    ),
    TestCase(
        "T05",
        "Edit a suggested treatment",
        "US4.2 (AC4.2.1, AC4.2.2)",
        _patient("T05 Elena Edit", 34, "female", 55),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Open Methylprednisolone and type: change dose to 40 mg",
            "Apply the edit, then reload the page.",
        ],
        [
            "An Edit treatment form opens with 40 mg filled in.",
            "After applying: the field shows edited, the panel says Edited by Dr. Maya, "
            "and the marker survives the reload.",
            "History export shows the original, the edit and who made it.",
        ],
    ),
    TestCase(
        "T06",
        "Explore an alternative pathway",
        "US3.6 (AC3.6.1, AC3.6.2)",
        _patient("T06 Fatima Explore", 34, "female", 62),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Type: explore infectious colitis",
            "Press Stop exploring.",
        ],
        [
            "Infectious colitis appears in a separate dashed lane; the main plan is unchanged.",
            "Stop exploring closes the lane; the audit marks it explored, not acted on.",
        ],
    ),
    TestCase(
        "T07",
        "Findings: unit conversion, invalid value, late details",
        "US3.1 (AC3.1.2, AC3.1.3)",
        _patient("T07 Grace Units", 34, "female", None),
        "34-year-old woman, bloody stool 6 months, Hb 102 g/L, calprotectin 850 µg/g",
        [
            "Look at the Hb chip before confirming.",
            "Change the Hb value to abc.",
            "Put it back to 10.2, confirm, and while the needs-data form is open type: "
            "she's 62 kg, also joint pain for 2 months",
        ],
        [
            "The chip reads Hb 10.2 g/dL (entered 102 g/L).",
            "abc marks the chip invalid and the walk cannot start.",
            "The patient card updates to 62 kg, the chat confirms, and Review findings and "
            "re-walk is offered.",
        ],
    ),
    TestCase(
        "T08",
        "Partial test results",
        "US3.3 (AC3.3.1, AC3.3.2)",
        _patient("T08 Hana Partial", 34, "female", 61),
        DEMO_TEXT,
        [
            "Confirm the findings.",
            "In the needs-data form fill only stool culture (negative); leave colonoscopy "
            "empty and submit.",
        ],
        [
            "The form names the tests it needs; the map marks them ?.",
            "Colonoscopy stays ? not yet tested; the walk ends as Needs data at suspected IBD.",
        ],
    ),
    TestCase(
        "T09",
        "Mild ulcerative proctitis",
        "Tier 1 path (mesalamine)",
        _patient("T09 Ivan Mild", 29, "male", 78),
        "29-year-old man, bloody stool 2 months, calprotectin 120 µg/g",
        [
            "Needs data: stool culture negative, colonoscopy ulcerative colitis; extent E1, "
            "severity mild."
        ],
        [
            "Reaches ulcerative proctitis, mild, with UC Tier 1 mesalamine.",
            "Watch the mesalamine line: the pack stores exactly 2 g, so another dose is held "
            "back as ungrounded.",
        ],
    ),
    TestCase(
        "T10",
        "High CRP typed at presentation",
        "Safety: a presenting CRP never skips a tier",
        _patient("T10 Jonas Highcrp", 41, "male", 72),
        "41-year-old man, bloody stool 3 months, stool frequency 4 per day, CRP 60 mg/L, "
        "Hb 11.8 g/dL",
        [
            "Needs data: stool culture negative, colonoscopy ulcerative colitis; extent E3, "
            "severity severe."
        ],
        [
            "CRP 60 is above the day-3 threshold of 45, yet the entry stays UC Tier 2.",
            "Tier 3 rescue is only a later planned step: only a day-3 result recorded on the "
            "criterion (T02) can move the entry.",
        ],
    ),
    TestCase(
        "T11",
        "Crohn's: mild ileal",
        "AC3.2.5 (Crohn's at the same depth)",
        _patient("T11 Kai Ileal", 26, "male", 75),
        "26-year-old man, abdominal pain 4 months, weight loss 3 kg, calprotectin 200 µg/g",
        [
            "Needs data: stool culture negative, colonoscopy Crohn's disease; location L1, "
            "behaviour B1, severity mild."
        ],
        ["Reaches ileal Crohn's with Crohn's Tier 1 oral budesonide."],
    ),
    TestCase(
        "T12",
        "Crohn's: moderate colonic, weight missing",
        "AC4.1.2 (weight-based dose), AC3.1.3",
        _patient("T12 Lena Noweight", 33, "female", None),
        "33-year-old woman, abdominal pain and diarrhoea 5 months, weight loss 4 kg, "
        "calprotectin 350 µg/g",
        [
            "Needs data: stool culture negative, colonoscopy Crohn's disease; location L2, "
            "behaviour B1, severity moderate.",
            "Open Infliximab 5 mg/kg IV.",
            "Type: she's 62 kg, then open Infliximab again.",
        ],
        [
            "Reaches Crohn's Tier 2 anti-TNF.",
            "With no weight, the dose says the weight is needed instead of guessing.",
            "After 62 kg: 310 mg, shown as 5 mg/kg × 62 kg = 310 mg.",
        ],
    ),
    TestCase(
        "T13",
        "Crohn's: penetrating",
        "Crohn's watch-outs (abscess)",
        _patient("T13 Mira Penetrating", 31, "female", 59),
        "31-year-old woman, abdominal pain 4 months, weight loss 6 kg, calprotectin 500 µg/g",
        [
            "Needs data: stool culture negative, colonoscopy Crohn's disease; location L3, "
            "behaviour B3, severity severe."
        ],
        ["Reaches penetrating Crohn's; watch-outs include the abscess path."],
    ),
    TestCase(
        "T14",
        "Safety checks on the patient card",
        "US4.1 (AC4.1.3), BR4 safety",
        _patient(
            "T14 Nora Safety",
            34,
            "female",
            70,
            allergies=["penicillin"],
            currentMedication=["methylprednisolone"],
            pregnancyStatus="pregnant",
        ),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Open Hydrocortisone and read its safety checks.",
        ],
        [
            "Allergy: No cross-reactivity with recorded allergies, citing the penicillin "
            "allergy node.",
            "Pregnancy: ? Not checked: no grounded safety data (never no conflict).",
            "Duplicate class: conflict, because methylprednisolone on the card is "
            "another corticosteroid.",
            "Interaction: ? Not checked where no interaction node applies.",
        ],
    ),
    TestCase(
        "T15",
        "Out of knowledge",
        "US3.4 (AC3.4.1)",
        _patient("T15 Omar Headache", 28, "male", 70),
        "28-year-old man, headache with visual aura for 2 days",
        ["Confirm the findings.", "Press Suggest adding this branch."],
        [
            "No grounded answer with the ⊘ mark; no diagnosis or treatment line.",
            "Suggest adding this branch opens the Knowledge screen.",
            "History filter Out of knowledge lists this session.",
        ],
    ),
    TestCase(
        "T16",
        "Case pinned to an older pack version",
        "US2.1 (AC2.1.3), FR1.7",
        _patient("T16 Priya Oldversion", 34, "female", 60),
        DEMO_TEXT,
        [
            "Open the case before typing anything.",
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Type: Remicade failed. steroids work.",
            "Press Re-walk on the banner, then type the same follow-up again.",
        ],
        [
            "The banner says a newer version is available; the pack chip says IBD 1.0.",
            "On 1.0 the follow-up gives No grounded answer (1.0 has no anti-TNF failure path).",
            "After re-walk on IBD 1.2 the same follow-up gives the post-anti-TNF plan.",
        ],
        pin="IBD@1.0",
    ),
    TestCase(
        "T17",
        "Care loop: prerequisites before a biologic",
        "Care-graph redesign: requires edges, To do first, results scoped to a treatment",
        _patient("T17 Dev Prereq", 34, "female", 64),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ")",
            "Type: Remicade failed. steroids work. Suggest alternate treatment plan (press Enter).",
            "Click Vedolizumab (a click only opens the panel), then press Choose this option.",
            "Open Latent tuberculosis screen: it is To do first. Pick negative, Record result.",
            "Open Hepatitis B screen and record negative.",
            "Now click Ustekinumab and Choose this option.",
        ],
        [
            "Choosing Vedolizumab lights both infection screens blue as To do first, with an "
            "arrow 'needs first', even if you gave screening results earlier.",
            "A cited note appears for the newly lit nodes; the Now on card lists To do first.",
            "A recorded result turns that screen Done and appears in the timeline strip.",
            "Choosing Ustekinumab asks for both screens again (a result counts for the "
            "treatment it was recorded for).",
        ],
    ),
    TestCase(
        "T18",
        "Care loop: symptom asserted, recurring test",
        "Care-graph redesign: if_present edges, Patient has this now, Watch for to Now",
        _patient("T18 Eli Signs", 34, "female", 60),
        DEMO_TEXT,
        [
            "Walk as in T01 (" + DEMO_TESTS + ") and choose Hydrocortisone.",
            "Open Toxic megacolon (Watch for) and press Patient has this now.",
            "Open Exclude infection at presentation and in flares and press Patient has this now.",
            "Open the stool culture test that comes back Due and record a result.",
            "Open CRP on intravenous steroids, record 30.",
        ],
        [
            "Monitoring and watch-out blocks never say Suggested: they read Due / Watch for.",
            "Toxic megacolon turns Present and Emergency colectomy triggers turns Now.",
            "The stool culture test returns as Due, then Done once a result is recorded.",
            "The focus view shows the current state; Show whole map reveals the rest.",
        ],
    ),
    TestCase(
        "U01",
        "Urology: small distal stone",
        "US9.1 (AC9.1.1, AC9.1.2)",
        _patient("U01 Raj Stone", 45, "male", 85),
        "45-year-old man with renal colic since yesterday, stone size 6 mm",
        ["Sign in as Demo urologist.", "Needs data: CT KUB ureteric stone."],
        ["Runs on the URO 0.1 pack chip and reaches Tier 1 observation with expulsive therapy."],
        owner=UROLOGIST,
    ),
    TestCase(
        "U02",
        "Urology: large stone",
        "US9.1, conditions that block a tier",
        _patient("U02 Sara Largestone", 50, "female", 68),
        "50-year-old woman with renal colic for 3 days, stone size 12 mm",
        ["Sign in as Demo urologist.", "Needs data: CT KUB ureteric stone."],
        ["The 12 mm stone is over the Tier 1 size limit, so no tier is entered."],
        owner=UROLOGIST,
    ),
]

APP_CHECKS = [
    (
        "Sign in and disclaimer (US1.1, US1.2)",
        [
            "Sign in as Dr. Maya: no password; name in the header.",
            "First sign-in: Accept and continue is disabled until both boxes are ticked.",
            "Decision support, not diagnosis and the pack version show on every screen.",
        ],
    ),
    (
        "Patients (US2.1)",
        [
            "The list opens with the T and U patients; searching a case ID finds it.",
            "Searching nonsense shows No patients found and Create new patient.",
        ],
    ),
    (
        "History (US7.1, US7.2)",
        [
            "After T01 and T15: filter by outcome, Replay on canvas (read-only map on the "
            "recorded version, chosen drug kept), Export JSON and PDF.",
        ],
    ),
    (
        "Knowledge (US8.1, US8.2)",
        [
            "Browse: walk nodes and edges freely.",
            "Update: source https://reference.medscape.com/drug/stelara-wezlana-ustekinumab-345050 "
            "plus a short note; a before/after card appears with the page cited.",
            "A note with no URL gets one follow-up question, never a loop.",
            "Sign in as Demo clinical reviewer to Approve and publish; IBD goes to 1.3 and "
            "old sessions keep their version.",
        ],
    ),
]


def guide_markdown() -> str:
    """docs/test-cases.md, generated from CASES and APP_CHECKS."""
    out = [
        "# Test cases",
        "",
        "Synthetic patients for testing every feature by hand. Decision support, not "
        "diagnosis. Every patient here is invented.",
        "",
        "## Reset and seed",
        "",
        "Stop the server first (Ctrl+C in its terminal), then from the project folder:",
        "",
        "```bash",
        ".venv/bin/python scripts/seed_test_cases.py",
        "```",
        "",
        "This deletes the old database and its cases (no migration) and creates the "
        "patients below. Start the server again afterwards. Each patient's chat opens with "
        "a note saying what to type first.",
        "",
        "Model: the live Meta model (`.env`) answers every case. The offline `recorded` "
        "provider (see README) only knows the demo text and the T03/T04 follow-ups, so "
        "only cases marked *offline* walk without a key.",
        "",
        "To keep your own database, seed a separate one and serve it on another port:",
        "",
        "```bash",
        ".venv/bin/python scripts/seed_test_cases.py --db data/test-cases.db",
        "```",
        "",
        "```bash",
        "set -a && source .env && set +a && BRAHMA_DB_PATH=data/test-cases.db "
        "BRAHMA_PORT=8001 .venv/bin/python -m brahma.server",
        "```",
        "",
        "## Run every case automatically",
        "",
        "`scripts/live_test_cases.py` plays each case's steps through the same API the web "
        "app uses, checks the expected results and writes `results/live-test-cases.md` "
        "(what the model returned and which screen component draws it). The walked cases "
        "stay in the database to open in the app.",
        "",
        "```bash",
        "BRAHMA_REHEARSAL_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/live_test_cases.py",
        "```",
        "",
        "## Cases",
        "",
        "| ID | Case | Covers | Profile |",
        "|---|---|---|---|",
    ]
    for c in CASES:
        who = "Demo urologist" if c.owner == UROLOGIST else "Dr. Maya"
        mark = " *(offline)*" if c.start == DEMO_TEXT else ""
        out.append(f"| {c.tid} | {c.title}{mark} | {c.covers} | {who} |")
    for c in CASES:
        p = c.patient
        card = [f"{p.age}, {p.sex}", f"{p.weight_kg:g} kg" if p.weight_kg else "no weight"]
        if p.allergies:
            card.append("allergies: " + ", ".join(p.allergies))
        if p.current_medication:
            card.append("medication: " + ", ".join(p.current_medication))
        if p.pregnancy_status:
            card.append(f"pregnancy: {p.pregnancy_status}")
        if c.pin:
            card.append(f"pinned to {c.pin.replace('@', ' ')}")
        out += [
            "",
            f"## {c.tid} · {c.title}",
            "",
            f"Card: {'; '.join(card)}.",
            "",
            f"Type first: `{c.start}`",
            "",
            "Steps:",
            "",
        ]
        out += [f"{i}. {s}" for i, s in enumerate(c.steps, 1)]
        out += ["", "Expect:", ""]
        out += [f"- {e}" for e in c.expect]
    out += ["", "## App checks (no special patient)", ""]
    for title, items in APP_CHECKS:
        out += [f"### {title}", ""] + [f"- {i}" for i in items] + [""]
    return "\n".join(out).rstrip() + "\n"


def server_running(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wipe(db_path: Path) -> list[str]:
    """Delete the database, its WAL files, the walk log and old scratch databases."""
    targets = [db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]
    log = Path(os.environ.get("BRAHMA_LOG_PATH", ROOT / "data" / "brahma.log"))
    targets.append(log)
    data = ROOT / "data"
    for stem in ("manual", "u4-smoke"):
        targets += sorted(data.glob(f"{stem}.*"))
    removed = []
    for path in targets:
        if path.exists():
            path.unlink()
            removed.append(str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path))
    return removed


def seed(db_path: Path) -> list[tuple[TestCase, str]]:
    """A fresh database with every pack, the demo profiles and one case per TestCase."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = ag_connect(db_path)  # same order as the server, so no trigger is "restored"
    knowledge = KnowledgeService(kg_connect(db_path))
    try:
        for archived in ARCHIVED_PACKS:
            knowledge.load_pack(archived)
        load_initial_packs(knowledge, ROOT / "content")
        ProfileRepository(conn).seed()
        ensure_up_schema(conn)
        cases = CaseService(conn, knowledge)
        made: list[tuple[TestCase, str]] = []
        # Newest first on the Patients page, so create the last case first.
        for case in reversed(CASES):
            stored = cases.create_case(case.patient, case.owner)
            if case.pin:
                pack, number = case.pin.split("@")
                cases.pin(stored.case_id, PackVersionRef(pack=pack, number=number))
            note = (
                f"Test case {case.tid}: {case.title} (synthetic patient). "
                f"To start, type: {case.start} — steps and what to expect are in "
                "docs/test-cases.md."
            )
            cases.append_message(
                stored.case_id, MessageIn(author="brahma", kind="text", body={"text": note})
            )
            made.append((case, stored.case_id))
        return list(reversed(made))
    finally:
        conn.close()
        knowledge.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, help="database path (default BRAHMA_DB_PATH)")
    parser.add_argument("--guide", action="store_true", help="only rewrite docs/test-cases.md")
    args = parser.parse_args()
    if args.guide:
        GUIDE.write_text(guide_markdown(), encoding="utf-8")
        print(f"Wrote {GUIDE.relative_to(ROOT)}")
        return 0
    db_path = args.db or Path(os.environ.get("BRAHMA_DB_PATH", ROOT / DEFAULT_DB_PATH))
    port = int(os.environ.get("BRAHMA_PORT", "8000"))
    if args.db is None and server_running(port):
        print(
            f"The server is running on port {port} and holds the database open.\n"
            "Stop it first (Ctrl+C in its terminal), then run this again.",
            file=sys.stderr,
        )
        return 1
    removed = wipe(db_path)
    print("Deleted: " + (", ".join(removed) if removed else "nothing (no old database)"))
    made = seed(db_path)
    print(f"Seeded {len(made)} synthetic test patients into {db_path}:")
    for case, case_id in made:
        who = "urologist" if case.owner == UROLOGIST else "Dr. Maya"
        print(f"  {case.tid}  {case_id}  {case.title}  ({who})")
    print("Steps and expected results: docs/test-cases.md. Start the server again now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
