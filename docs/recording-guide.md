# Demo recording guide

Target: one clean take, about 5 minutes, ending on 0 ungrounded lines.
Record November 2-4 on the live Meta model. Submit before Nov 4, 9 PM ET.

## 1. Before you press record

- Check out the tagged commit the video is recorded from, and make NO commits
  after the tag until the video is submitted.
- `set -a && source .env && set +a` with the live Meta key configured.
- Keep the Mac awake and on stable network for the whole session
  (`caffeinate -i` in a spare terminal). Sleep once stalled a walk for ~60 min.
- Free ports 8000-8003. Close anything that might notify or sleep the disk.
- Rehearse once unrecorded: `BRAHMA_REHEARSAL_ALL=1 scripts/live_rehearsal.py`
  takes ~75 s and ends at 0-1 ungrounded. If it ends at 1, just run it again.

## 2. The script (demo patient: 34F, bloody stool, Hb 10.2, calprotectin 850)

1. **Sign in + disclaimer** (10 s). Dr. Maya profile, accept the disclaimer.
2. **New patient, start the walk** (30 s). Paste the vignette, confirm the
   extracted findings. Point out the map lighting up beside the chat.
3. **Needs-data rounds** (60 s). Answer stool culture negative, biopsy UC,
   extent E3, severity severe. Each answer extends the map: diagnosis ->
   sub-type -> treatment tier -> monitoring.
4. **The grounded badge** (20 s). End of walk: 0 ungrounded lines. Open one
   line's citations to show the source trail.
5. **Choose the drug + edit** (45 s). The Tier 2 drugs are grey options.
   Open Hydrocortisone, show dose and day-3 review, press Choose this option (a click only opens the panel; the buttons record),
   show its monitoring lighting up blue plus the "Now on" next-step card.
   Edit a note, show the edited marker.
6. **Day-3 review** (35 s). Open the day-3 CRP criterion from the monitor
   column ("If met → UC Tier 3"), record 20: the tier stands. Record 60:
   the review opens Tier 3 as a new walk, still 0 ungrounded. Open Toxic
   megacolon to show its "Where it leads" colectomy path.
7. **Follow-up** (40 s). "Remicade failed, steroids work." Show the walk
   switching to the post-anti-TNF tier with the tried drug marked.
8. **Why + audit** (30 s). Open the why panel, then the audit trail replay.
9. **Knowledge update** (40 s). Propose a change in plain language with a
   source URL, answer the follow-up question, publish as reviewer.
10. **Benchmark page** (20 s). Open `results/benchmark.html`: graph vs the
    same model with no knowledge base, on grounded share and pathway
    agreement.

## 3. Takes and recovery

- Record at least 3 full takes; ship a take that ends at 0 ungrounded. The
  held-back count is visible on screen, so a 1-line take is still honest,
  just weaker.
- If a walk stalls mid-section (no new lines for 3+ minutes), stop the take:
  retry the walk rather than waiting it out.
- If the model is unavailable, wait 10 minutes and retry once before calling
  it a day.

## 4. Submission checklist

- [ ] Video recorded from the tagged commit, no commits after the tag.
- [ ] Video uploaded, link works in a private window.
- [ ] Repo public at https://github.com/barnikbh/brahma with README demo steps.
- [ ] `results/benchmark.html` committed from the final run.
- [ ] Submission filed before Nov 4, 9 PM ET.
