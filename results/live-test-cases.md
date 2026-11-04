# Live test cases

Model: `{'status': 'ok', 'packs': [{'pack': 'IBD', 'number': '1.2'}, {'pack': 'URO', 'number': '0.1'}], 'provider': {'provider': 'meta', 'model': 'muse-spark-1.3'}, 'database': 'ok', 'disclaimer': 'Decision support, not diagnosis'}`. Checks passed: **16 / 16**. Synthetic cases only; decision support, not diagnosis.

| Case | Checks | Time | Ungrounded | Notes |
|---|---|---|---|---|
| T17 | 10/10 | 233s | [0, 1] | ok |
| T18 | 6/6 | 147s | [0] | ok |

## T17 · BR-F4CD52

- ✓ walk ends answered
- ✓ 0 ungrounded lines (1 tolerated live)
- ✓ walk ends answered
- ✓ 0 ungrounded lines (1 tolerated live)
- ✓ choice recorded
- ✓ both screens To do first
- ✓ result recorded
- ✓ TB screen Done
- ✓ card lines are grounded (0 rejected)
- ✓ screens asked again

| Step | Time | Events | Drawn by |
|---|---|---|---|
| start walk | 8.9s | progress×1, form×1, paused×1 | ChatForm (confirm-findings chips / needs-data); ChatForm waiting state; ChatThread progress line |
| confirm findings | 0.0s | progress×1, map_update×1, form×1, paused×1 | ChatForm (confirm-findings chips / needs-data); ChatForm waiting state; ChatThread progress line; GraphCanvas (map) |
| answer needs-data IBD-N20=negative, IBD-N21=ulcerative colitis | 0.0s | progress×1, map_update×1, form×1, paused×1 | ChatForm (confirm-findings chips / needs-data); ChatForm waiting state; ChatThread progress line; GraphCanvas (map) |
| answer needs-data IBD-N22=E3, IBD-N23=severe | 147.1s | progress×10, map_update×1, line×36, section_done×9, done×1 | ChatLine + NodeChip (cited line); ChatThread progress line; ChatThread section header; GraphCanvas (map); WalkSummary + ResultBadge |
| follow-up: Remicade failed | 67.7s | progress×4, history×1, map_update×1, line×10, section_done×3, done×1 | ChatLine + NodeChip (cited line); ChatThread notice (treatment history); ChatThread progress line; ChatThread section header; GraphCanvas (map); WalkSummary + ResultBadge |
| choose Vedolizumab | 0.01s | HTTP 201 |  |
| TB screen negative | 0.01s | HTTP 201 |  |
| cited card for the lit nodes | 9.09s | HTTP 200 |  |
| choose Ustekinumab | 0.01s | HTTP 201 |  |

Extracted chips: age 34.0; sex woman; bloody stool 6 months; Hb 10.2 g/dL; calprotectin 850.0 ug/g

> Noted treatment history: infliximab — no response; corticosteroid — responded.

## T18 · BR-2C4F94

- ✓ walk ends answered
- ✓ 0 ungrounded lines (1 tolerated live)
- ✓ CRP monitoring is Due, not Suggested
- ✓ megacolon Present, colectomy Now
- ✓ stool culture Due again
- ✓ stool culture Done

| Step | Time | Events | Drawn by |
|---|---|---|---|
| start walk | 8.0s | progress×1, form×1, paused×1 | ChatForm (confirm-findings chips / needs-data); ChatForm waiting state; ChatThread progress line |
| confirm findings | 0.0s | progress×1, map_update×1, form×1, paused×1 | ChatForm (confirm-findings chips / needs-data); ChatForm waiting state; ChatThread progress line; GraphCanvas (map) |
| answer needs-data IBD-N20=negative, IBD-N21=ulcerative colitis | 0.0s | progress×1, map_update×1, form×1, paused×1 | ChatForm (confirm-findings chips / needs-data); ChatForm waiting state; ChatThread progress line; GraphCanvas (map) |
| answer needs-data IBD-N22=E3, IBD-N23=severe | 139.3s | progress×10, map_update×1, line×39, section_done×9, done×1 | ChatLine + NodeChip (cited line); ChatThread progress line; ChatThread section header; GraphCanvas (map); WalkSummary + ResultBadge |
| choose Hydrocortisone | 0.01s | HTTP 201 |  |
| toxic megacolon present | 0.01s | HTTP 201 |  |
| new bloody diarrhoea present | 0.0s | HTTP 201 |  |
| stool culture negative | 0.0s | HTTP 201 |  |

Extracted chips: age 34.0; sex woman; bloody stool 6 months; Hb 10.2 g/dL; calprotectin 850.0 ug/g
