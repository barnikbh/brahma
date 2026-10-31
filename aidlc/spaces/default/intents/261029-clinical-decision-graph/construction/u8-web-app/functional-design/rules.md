# Business Rules — u8-web-app

Upstream: `functional-spec.md` (U8), `stories.md`, `requirements.md` (FR5, FR6, FR9–FR12, FR15, NFR3), `mockups.md`, `accessibility-checklist.md`.

## Shell and sign-in (BR1)

- **BR1.1** Sign-in lists the demo profiles as cards. Picking one signs in without a password and lands on Patients, with the profile name shown in the header.
- **BR1.2** "Decision support, not diagnosis" and the live pack chips (for example IBD v1.0, URO v0.1) appear in the header on every screen after sign-in, and in every walk summary.
- **BR1.3** On first sign-in, "Accept and continue" stays disabled until both disclaimer boxes are ticked.

## Patients (BR2)

- **BR2.1** Search runs as you type, after a 250 ms pause. When nothing matches, the page shows "No patients found" and "Create new patient".
- **BR2.2** "Create new patient" opens a new case. Its generated ID is labelled "synthetic".
- **BR2.3** A reopened case shows its pinned version. When a newer version is live, the banner "Newer version vX.Y available: re-walk?" appears.

## Workspace (BR3)

- **BR3.1** Forms are rendered from `form` events (confirm findings, needs data, patient details, edit treatment), with validation states for invalid, conflict and confirm-range. A partly filled needs-data form can still be submitted. Once submitted, a form shrinks to a one-line summary.
- **BR3.2** Only `line` events produce answer text, and each line shows its node chips under a fixed section header. Nothing else from the model is ever rendered.
- **BR3.3** Progress labels appear as `progress` events arrive. A summary shows steps, cited, ungrounded, pack version and provider.
- **BR3.4** "Out of knowledge" shows "No grounded answer", the ⊘ symbol and "Suggest adding this branch". On error, the workspace shows the message and a Retry button, and keeps every input.
- **BR3.5** The patient card stays at the top. Below it, the chat sits on the left and the map on the right. The map uses fixed columns, and nodes and edges light up in walk order as `map_update` events arrive.
- **BR3.6** Selecting a chat line selects its node and opens its panel. Selecting a node highlights its line. Both work with Enter and Space.
- **BR3.7** Every result shows a symbol and a word as well as a colour. The five NFR3 accessibility items apply.
- **BR3.8** Explore opens a separate lane on the map and in the chat, and the main plan doesn't change. "Stop exploring" closes the lane.
- **BR3.9** A second tab on the same case shows a read-only banner and disables input.

## Node panel (BR4)

- **BR4.1** The panel shows the node's type, drug, route, dose and dose formula, frequency, review point, sources, version and comments.
- **BR4.2** Safety shows "! Allergy conflict" with the node chip, or "? Not checked: no grounded safety data". It never shows "no conflict" unless a node supports it.
- **BR4.3** After an edit, the field shows "✎ edited" and the panel shows "Edited by <profile>".

## History (BR5)

- **BR5.1** History has outcome and text filters. With no sessions, it shows "No sessions yet".
- **BR5.2** A session's detail shows its inputs, its answer, and the "why" with node chips.
- **BR5.3** Replay shows the session's path read-only, on the version the session recorded.
- **BR5.4** Export downloads the session as JSON or PDF.

## Knowledge (BR6)

- **BR6.1** The proposal form takes a node, a source URL, the change and a comment. If submitting fails, the input stays and the reason is shown.
- **BR6.2** The copy flag is shown, and Publish is disabled while it is set.
- **BR6.3** The reviewer sees the before and after, the source passage, the proposer and their comment, with Publish and Reject buttons. Version history lists every version.

## Summary

There are 25 rules in six groups. The web app shows only answer text that has passed the check, and every screen carries the disclaimer.
