# Clinical review checklist (IBD pack v1.1 + URO v0.1)

All pack content was drafted by Claude from the cited guidelines and has NOT
been checked by a doctor. Nothing here is a diagnosis or a prescription: Brahma
is decision support, and every line it shows must trace to a source below.

Files under review: `content/ibd.yaml` (IBD v1.1), `content/urology.yaml`
(URO v0.1), and the benchmark's expected pathways
(`results/benchmark_cases.json`, appendix A).

## 1. Drug doses (verify each against its cited source)

| Node | Drug | Pack says | Sources |
|---|---|---|---|
| IBD-N50 | Mesalamine | 2 g oral once daily (range 2-3 g); maintenance | IBD-S4 |
| IBD-N51 | Hydrocortisone | 100 mg IV four times daily to day-3 review | IBD-S2 |
| IBD-N52 | Methylprednisolone | 60 mg IV once daily to day-3 review | IBD-S2 |
| IBD-N53 | Infliximab | 5 mg/kg IV at weeks 0, 2, 6, then every 8 weeks; single infusion as rescue | IBD-S1, S5, S6 |
| IBD-N54 | Ustekinumab | ~6 mg/kg IV induction once, then 90 mg SC every 8 weeks | IBD-S5, S19 |
| IBD-N55 | Budesonide | 9 mg oral once daily, induction only, ileocaecal CD | IBD-S5, S6 |
| IBD-N57 | Vedolizumab | 300 mg IV at weeks 0, 2, 6, then every 8 weeks | IBD-S1, S19 |
| IBD-N58 | Tofacitinib | 10 mg oral twice daily for 8 weeks induction | IBD-S1?, S20 |
| IBD-N56 | Levothyroxine | ~1.6 ug/kg/day (comorbidity demo node, not IBD care) | IBD-S16 |

## 2. Thresholds and criteria

- Calprotectin above 50 ug/g supports referral (N5; IBD-S10).
- Truelove and Witts severity from stool frequency, blood, pulse, temperature,
  Hb and ESR (N23; IBD-S2, S1).
- Day 3 on IV steroids: more than 8 stools/day, or CRP above 45 mg/L with 3-8
  stools/day, predicts colectomy is likely (N70, N71; IBD-S2).
- Rescue (N41 -> N42) fires when stool frequency is above 8/day OR CRP is above
  45 mg/L (edges IBD-E34, E35).
- Infliximab trough target at least 5 ug/mL after loss of response (N72;
  IBD-S13).
- Calprotectin target 250 ug/g or below (N82; IBD-S12).
- Montreal extent E1-E3, CD location L1-L3, behaviour B1-B3 (IBD-S9).

## 3. Known gaps found while building the benchmark

These are pack-design questions, not code bugs. Please rule on each:

1. **Stool culture gates nothing.** N20 collects negative/positive and N13
   (infectious colitis) exists as an `alternative_to`, but NO edge condition
   references the stool-culture result. A positive C. difficile result changes
   no pathway. Should a positive result block or redirect the IBD tiers?
2. **E1 proctitis is oral-only.** Tier 1 (N50) is oral mesalamine for all mild
   to moderate UC including E1 proctitis. Most guidelines put rectal 5-ASA
   first-line for proctitis. Confirm oral-only, or add a topical option.
3. **Missing day-3 values still show rescue.** Acute severe UC with unknown
   stool frequency/CRP includes the rescue tier N42 (missing input walks the
   escalation as an option to discuss). Intended, but confirm you are happy
   the demo presents rescue before the values exist.
4. **v1.1 anti-TNF-failure nodes are unreviewed.** N46 (switch class), N54/N57/
   N58 (ustekinumab/vedolizumab/tofacitinib), N72 (trough), N83/N92/N95/N99/
   N102/N103 (response, monitoring, clot/heart warning, surgery) were added
   for the follow-up demo and never clinically checked.

## 4. Urology pack (v0.1, small)

- CT KUB confirms ureteric stone; stone size at most 10 mm vs above 10 mm
  routes the pathway. Confirm the 10 mm cut is the one you want cited.

## 5. Sign-off

For each benchmark case you approve, set `reviewedBy` to your name in
`results/benchmark_cases.json` and re-run the benchmark so the report carries
it:

    set -a && source .env && set +a && .venv/bin/python scripts/run_benchmark.py

Then note the approved pack versions and date in `HANDOFF.md` (issue 12).

## Appendix A. Expected pathways under review

IBD v1.1, URO v0.1 (regenerate with
`.venv/bin/python scripts/run_benchmark.py --expected-only`):

    uc-acute-severe (21): IBD-N10, N11, N20-N23, N32, N34, N41, N42, N51, N52,
      N60, N70, N71, N80, N81, N90, N91, N94, N96
    uc-mild-proctitis (13): IBD-N10, N11, N20-N23, N30, N33, N40, N50, N60, N82, N94
    uc-moderate-leftsided (13): IBD-N10, N11, N20-N23, N31, N33, N40, N50, N60,
      N82, N94
    uc-severe-e2 (21): IBD-N10, N11, N20-N23, N31, N34, N41, N42, N51, N52, N60,
      N70, N71, N80, N81, N90, N91, N94, N96
    uc-day3-responder (20): IBD-N10, N11, N20-N23, N32, N34, N41, N51, N52, N60,
      N70, N71, N80, N81, N90, N91, N94, N96 (no N42 rescue: responding)
    cd-ileal-mild (15): IBD-N10, N12, N20, N21, N24-N26, N35, N43, N44, N55, N61,
      N84, N94, N98
    cd-colonic-moderate (16): IBD-N10, N12, N20, N21, N24-N26, N36, N44, N45,
      N53, N61, N72, N85, N92, N94
    cd-ileocolonic-severe (16): IBD-N10, N12, N20, N21, N24-N26, N37, N44, N45,
      N53, N61, N72, N85, N92, N94
    cd-stricturing (17): IBD-N10, N12, N20, N21, N24-N26, N35, N38, N43, N44,
      N55, N61, N84, N94, N97, N98
    cd-penetrating (18): IBD-N10, N12, N20, N21, N24-N26, N37, N39, N44, N45,
      N53, N61, N72, N85, N92, N93, N94
    uro-distal-small (6): URO-N2, N3, N5-N8
    uro-large (3): URO-N2, N3, N5

## New in IBD 1.2 (care loop) for the reviewer

Clinical links added in 1.2 (all cite existing sources; please confirm each):
- IBD-N110 latent tuberculosis screen and IBD-N111 hepatitis B screen (source IBD-S15), required (must) before infliximab (N53), ustekinumab (N54), vedolizumab (N57) and tofacitinib (N58). Is "must" right for all four, and should a result stay valid for some days (the pack supports `validForDays`)?
- Toxic megacolon (N90) leads to Emergency colectomy triggers (N96) when present; new or worsening bloody diarrhoea (N94) brings the stool tests (N20) back.
- Moved in 1.2 (logic review, Nov 4): infliximab trough level (N72) now hangs off infliximab (N53), not the Tier 3 / Crohn's anti-TNF tiers (the after-anti-TNF tier N46 keeps its own "check levels" link); the JAK clot and heart risk (N103) hangs off tofacitinib (N58); toxic megacolon (N90), clot risk in hospital (N91) and emergency colectomy triggers (N96) hang off acute severe UC (N34), so they are watched from admission rather than after a steroid is chosen. The tier links to "Screen for infection before biologics" (N92) were removed: the real screens (N110, N111) replace that note.
