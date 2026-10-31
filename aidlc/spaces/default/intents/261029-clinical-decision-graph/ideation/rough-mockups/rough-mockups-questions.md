# Rough Mockups — Questions

Context: the doctor app has simple sign-in, chat and a canvas of the knowledge-graph region in use; the visual design is yours (scope-document.md, intent-backlog.md IB-06, IB-07; constraint C-O6).

## Q1. [Design] Your design drafts

You said you'd share design drafts for the app. How should this stage use them?

A. I'll share them now (paste images or give a file path); the wireframes follow them
B. Not ready yet: draft rough wireframes now as a starting point, and replace them when my drafts arrive
C. Not ready yet: skip detailed wireframes for now and capture only the user flow and screen list
D. Not yet defined
X. Other (please specify)

[Answer]: A (you'll share your own wireframes, generated from a PM write-up of your user story; this stage's wireframes follow them)

## Q2. [Design] Main screen layout

The consultation screen holds the chat and the canvas. How should they share the screen?

A. Split view: chat on the left, canvas on the right, with the canvas lighting up the path as the agent walks it
B. Canvas-centred, with the chat in a side drawer
C. Chat-centred, with the canvas opening on demand
D. Not yet defined
X. Other (please specify)

[Answer]: A (from your wireframes: chat on the left, the network map on the right; the path lights up as Brahma walks it; screens 04–13)

## Q3. [Design] How the agent's answer looks

The answer is the doctor's pathway, and every step must show its source. How should it be presented?

A. A structured pathway card (working diagnosis → confirm with → sub-type → treatment tiers → monitor → diet → watch-outs and escalation); each line carries a citation chip that highlights its node on the canvas
B. Conversational text with inline citations
C. Both: a short text summary above the structured pathway card
D. Not yet defined
X. Other (please specify)

[Answer]: C (from your wireframes: a summary line with step, cited and ungrounded counts above the structured pathway, each line with a node chip N1–N18; screen 08)

## Q4. [Design] How the doctor enters the patient's picture

Symptoms and metrics drive the walk (e.g. symptom and duration, lab values with units). How does the doctor enter them?

A. Free text in the chat
B. A structured intake form (symptoms, durations, metrics with values and units)
C. Free text, which the agent turns into editable chips (symptom, duration, metric value) before it walks
D. Not yet defined
X. Other (please specify)

[Answer]: C (from your wireframes: free text in the chat, read back as an editable "Confirm findings" form of chips before the walk; screen 05)

## Q5. [Design] Screens beyond the consultation (select all that apply)

Which other screens does the first version need?

A. Session audit and history: past sessions, each with its path, sources and explanation
B. Knowledge update: link a source or submit a change, and see versions with comments
C. Node detail panel: a node's content, source, version and comments, opened from the canvas
D. Benchmark results page: the 20 cases and their grounded-answer scores
X. Other (please specify)

[Answer]: A, B, C, D, X (from your wireframes: all four, plus Patients landing, first sign-in disclaimer and tour, explore a side pathway, edit treatment, generate prescription, follow-up visit with trends)

## Q6. [Design] Devices and accessibility

Which devices must work, and what accessibility level?

A. Desktop and laptop only, with WCAG 2.1 AA basics (keyboard navigation, contrast, never color alone)
B. Desktop plus tablet, same accessibility basics
C. Desktop, tablet and phone, same accessibility basics
D. Not yet defined
X. Other (please specify)

[Answer]: A (from your wireframes: desktop and laptop at 1440 px, WCAG 2.1 AA basics; tablet is listed as low priority and an open question)

## Q7. [Scope] Crohn's disease in the first version

The approved scope has Crohn's disease at the same depth as ulcerative colitis (a Must, scope-document.md). Your wireframes show Crohn's as "not in this pack" (⊘) in IBD v1.3, and the benchmark as 16 IBD + 4 urology cases. Which holds?

A. Keep the scope: Crohn's is authored to full depth; the wireframes' ⊘ on Crohn's is only an example of the out-of-knowledge state
B. Follow the wireframes: drop Crohn's from v1 and use it as the live out-of-knowledge demo
C. Middle: Crohn's to diagnosis and sub-type only, no treatment tiers
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. [Scope] Screens added beyond the approved scope

Your wireframes add generate prescription (sign to PDF), follow-up visit with trend charts, explore a side pathway, edit treatment, and the first sign-in tour. None is in the approved scope, and the schedule has no slack (scope-document.md, Scope-vs-Timeline Check). How should the first version treat them?

A. Build them all for Nov 2, accepting the extra schedule risk
B. Core walk plus explore and edit treatment for Nov 2; prescription, follow-up and tour are stretch goals built only after feature-complete
C. Core walk only for Nov 2; all five are stretch goals
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Wireframes follow your Brahma design handover (`docs/design-handover/`): 26 screens and states, indigo + sage, chat-first (Q1)
- Main screen: split view, consultation chat on the left and the network map of the graph region on the right, with a sticky patient card above both; the path lights up in walk order (Q2)
- Answer: a summary line (sub-type, entry tier, cited and ungrounded counts) above the structured pathway, every line carrying a node chip that selects its node on the map (Q3)
- Patient input: free text in the chat, read back as an editable "Confirm findings" form before the walk; Brahma asks for anything else through forms in the chat (Q4)
- Screens: sign-in, first sign-in disclaimer and tour, Patients, the workspace in all its states, node detail, session history and audit, knowledge update with versions, benchmark (Q5)
- Devices: desktop and laptop, WCAG 2.1 AA basics, status never shown by colour alone; tablet stays out (Q6)
- Crohn's disease stays at full depth as approved; the ⊘ on Crohn's in the wireframes is only an example of the out-of-knowledge state, and the benchmark covers both UC and Crohn's (Q7)
- Explore, edit treatment, generate prescription, follow-up visit with trends, and the first sign-in tour are all built for the Nov 2 feature-complete date, accepting the extra schedule risk (Q8)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
