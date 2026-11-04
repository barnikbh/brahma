"""The deterministic graph walk on the real packs (plan Step 11; BR2.2-BR2.4, BR2.10,
AC3.2.1, AC3.2.5, AC3.3.1, AC3.3.2, AC3.4.1, AC9.1.1, AC9.1.2)."""

from __future__ import annotations

from brahma.agent.traverse import choose_version, lane_nodes, walk_graph
from brahma.agent.views import build_map
from brahma.knowledge import Fact, KnowledgeService, PackVersionRef

IBD = PackVersionRef(pack="IBD", number="1.2")
URO = PackVersionRef(pack="URO", number="0.1")
DEMO_FINDINGS = [
    Fact(kind="finding", name="bloody stool"),
    Fact(kind="finding", name="Hb", value=10.2, unit="g/dL"),
    Fact(kind="finding", name="calprotectin", value=850, unit="ug/g"),
]
DEMO_TESTS = [
    Fact(kind="test", name="stool culture", value="negative"),
    Fact(kind="test", name="colonoscopy", value="ulcerative colitis"),
    Fact(kind="test", name="disease extent", value="E3"),
    Fact(kind="test", name="uc severity", value="severe"),
]


def test_demo_findings_reach_severe_pancolitis_with_tier_2_entry(
    knowledge: KnowledgeService,
) -> None:
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS])
    assert trav.outcome == "walked"
    assert trav.section("findings") == ["IBD-N1", "IBD-N3", "IBD-N5"]
    assert trav.section("diagnosis") == ["IBD-N10", "IBD-N11"]
    assert trav.section("subtype") == ["IBD-N32", "IBD-N34"]
    assert trav.entry_tier_ids == ["IBD-N41"]
    assert trav.section("treatment")[:3] == ["IBD-N41", "IBD-N51", "IBD-N52"]
    assert {"IBD-N70", "IBD-N80"} <= set(trav.section("monitor"))
    assert trav.section("diet") == ["IBD-N60"]
    assert {"IBD-N90", "IBD-N96"} <= set(trav.section("watch_outs"))
    assert trav.needed_tests == []
    assert trav.statuses()["IBD-N13"] == "not_taken"


def test_a_crohns_case_reaches_its_subtype_and_tiers(knowledge: KnowledgeService) -> None:
    facts = [
        Fact(kind="finding", name="abdominal pain"),
        Fact(kind="finding", name="weight loss"),
        Fact(kind="test", name="colonoscopy", value="crohn's disease"),
        Fact(kind="test", name="crohn's location", value="L1"),
        Fact(kind="test", name="crohn's activity", value="moderate"),
    ]
    trav = walk_graph(knowledge, IBD, facts)
    assert trav.section("diagnosis") == ["IBD-N10", "IBD-N12"]
    assert trav.section("subtype") == ["IBD-N35"]
    assert trav.entry_tier_ids == ["IBD-N43"]
    assert "IBD-N55" in trav.section("treatment")
    assert trav.section("diet") == ["IBD-N61"]


def test_missing_tests_are_named_as_needed(knowledge: KnowledgeService) -> None:
    trav = walk_graph(knowledge, IBD, DEMO_FINDINGS)
    assert trav.needed_tests == ["IBD-N20", "IBD-N21"]
    assert "subtype" not in trav.sections
    assert trav.statuses()["IBD-N21"] == "test_needed"


def test_a_partial_answer_goes_as_far_as_the_data_allows(knowledge: KnowledgeService) -> None:
    facts = [*DEMO_FINDINGS, DEMO_TESTS[1], DEMO_TESTS[2]]  # no stool culture, no severity
    trav = walk_graph(knowledge, IBD, facts)
    assert trav.section("subtype") == ["IBD-N32"]
    assert trav.needed_tests == ["IBD-N23"]
    assert trav.entry_tier_ids == []
    assert trav.test_results == {"IBD-N21": "ulcerative colitis", "IBD-N22": "E3"}


def test_crohns_without_activity_asks_for_it(knowledge: KnowledgeService) -> None:
    facts = [
        Fact(kind="finding", name="abdominal pain"),
        Fact(kind="test", name="colonoscopy", value="crohn's disease"),
        Fact(kind="test", name="crohn's location", value="L1"),
    ]
    trav = walk_graph(knowledge, IBD, facts)
    assert "IBD-N26" in trav.needed_tests
    assert trav.entry_tier_ids == []


def test_headache_with_aura_is_out_of_knowledge(knowledge: KnowledgeService) -> None:
    facts = [Fact(kind="finding", name="headache with visual aura")]
    assert choose_version(knowledge, facts, None) is None
    assert walk_graph(knowledge, IBD, facts).outcome == "out_of_knowledge"
    assert choose_version(knowledge, facts, IBD) is None


def test_a_urology_case_uses_the_urology_pack(knowledge: KnowledgeService) -> None:
    facts = [
        Fact(kind="finding", name="renal colic"),
        Fact(kind="finding", name="stone size", value=6, unit="mm"),
    ]
    version = choose_version(knowledge, facts, IBD)  # a pin on IBD does not stop it
    assert version == URO
    first = walk_graph(knowledge, URO, facts)
    assert first.needed_tests == ["URO-N3"]
    trav = walk_graph(
        knowledge, URO, [*facts, Fact(kind="test", name="ct kub", value="ureteric stone")]
    )
    assert trav.section("subtype") == ["URO-N5"]
    assert trav.entry_tier_ids == ["URO-N6"]
    assert trav.section("watch_outs") == ["URO-N7", "URO-N8"]


def test_the_explore_lane_holds_the_branch_and_its_tests(knowledge: KnowledgeService) -> None:
    assert lane_nodes(knowledge, IBD, "IBD-N13") == ["IBD-N13", "IBD-N20"]
    assert choose_version(knowledge, DEMO_FINDINGS, IBD) == IBD


def test_offered_drugs_are_options_and_tier_downstream_is_planned(
    knowledge: KnowledgeService,
) -> None:
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS])
    statuses = trav.statuses()
    assert statuses["IBD-N41"] == "entry"
    assert statuses["IBD-N51"] == "option"
    assert statuses["IBD-N52"] == "option"
    for node_id in (
        "IBD-N70",
        "IBD-N71",
        "IBD-N80",
        "IBD-N81",
    ):
        assert statuses[node_id] == "planned"
    # Acute severe UC's own risks are watched from admission, not after a drug choice.
    for node_id in ("IBD-N90", "IBD-N91", "IBD-N96"):
        assert statuses[node_id] == "used"
    assert statuses["IBD-N42"] == "planned"  # the escalation tier is a future step
    assert statuses["IBD-N60"] == "used"  # diet comes from the traversed subtype
    assert statuses["IBD-N94"] == "used"  # exclusion comes from the traversed diagnosis
    assert statuses["IBD-N13"] == "not_taken"


def test_a_choice_marks_the_drug_chosen_and_lights_its_tier(
    knowledge: KnowledgeService,
) -> None:
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS])
    trav.choices = {"IBD-N41": "IBD-N51"}
    statuses = trav.statuses()
    assert statuses["IBD-N51"] == "chosen"
    assert statuses["IBD-N52"] == "option"
    for node_id in (
        "IBD-N70",
        "IBD-N71",
        "IBD-N80",
        "IBD-N81",
        "IBD-N90",
        "IBD-N91",
        "IBD-N96",
    ):
        assert statuses[node_id] == "used"
    assert statuses["IBD-N42"] == "planned"
    assert statuses["IBD-N41"] == "entry"


def test_tried_beats_option_and_a_stale_choice_lights_nothing(
    knowledge: KnowledgeService,
) -> None:
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS])
    trav.tried = {"IBD-N51": "failed"}
    trav.choices = {"IBD-N41": "IBD-N51", "IBD-N42": "IBD-N99"}
    statuses = trav.statuses()
    assert statuses["IBD-N51"] == "tried"
    assert statuses["IBD-N70"] == "planned"


def test_crohns_options_cover_the_entry_tiers_drugs(knowledge: KnowledgeService) -> None:
    facts = [
        Fact(kind="finding", name="abdominal pain"),
        Fact(kind="finding", name="weight loss"),
        Fact(kind="test", name="colonoscopy", value="crohn's disease"),
        Fact(kind="test", name="crohn's location", value="L1"),
        Fact(kind="test", name="crohn's activity", value="moderate"),
    ]
    trav = walk_graph(knowledge, IBD, facts)
    statuses = trav.statuses()
    assert statuses["IBD-N43"] == "entry"
    assert trav.option_ids
    assert all(statuses[n] == "option" for n in trav.option_ids)


def test_option_edges_are_dashed_until_their_drug_is_chosen(
    knowledge: KnowledgeService,
) -> None:
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS])
    before = {e.edge_id: e.style for e in build_map(knowledge, IBD, trav, "IBD 1.2").edges}
    assert before["IBD-E30"] == "not_taken"
    assert before["IBD-E31"] == "not_taken"
    assert before["IBD-E37"] == "not_taken"
    trav.choices = {"IBD-N41": "IBD-N51"}
    after = {e.edge_id: e.style for e in build_map(knowledge, IBD, trav, "IBD 1.2").edges}
    assert after["IBD-E30"] == "walked"
    assert after["IBD-E31"] == "not_taken"
    assert after["IBD-E37"] == "walked"


def test_a_review_scoped_crp_moves_the_entry_tier_to_tier_3(
    knowledge: KnowledgeService,
) -> None:
    review_crp = Fact(kind="finding", name="CRP", value=60, unit="mg/L", context="review")
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS, review_crp])
    assert trav.entry_tier_ids == ["IBD-N42"]
    assert trav.section("treatment")[0] == "IBD-N42"


def test_a_presenting_crp_never_moves_the_entry_tier(
    knowledge: KnowledgeService,
) -> None:
    presenting_crp = Fact(kind="finding", name="CRP", value=60, unit="mg/L")
    trav = walk_graph(knowledge, IBD, [*DEMO_FINDINGS, *DEMO_TESTS, presenting_crp])
    assert trav.entry_tier_ids == ["IBD-N41"]
