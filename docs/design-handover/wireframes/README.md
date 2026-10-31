# Brahma — Wireframes

Exported 29 Oct 2026 from the live canvas: https://claude.ai/artifact/9P9tgvea8bc5hBj5JoBKfr
Spec: ../design-handover/Brahma - Design Handover.md

## What's here

| Folder / file | What it is |
| --- | --- |
| `Brahma - Wireframes.pdf` | Every screen and key state, one per page, for sharing and review |
| `screens/` | Full-page PNG of each screen and state (1440 px wide; graph options 900 px) |
| `html/` | The clickable wireframes: one `.dc.html` per screen, `support.js` runtime, `canvas.json` layout |

## Open the clickable HTML

The screens load each other, so they need a local web server (opening a file directly won't work).

- **Mac:** double-click `html/Open wireframes.command`. If macOS blocks it, right-click → Open. Close the Terminal window to stop.
- **Any OS:** in a terminal, `cd html && python3 -m http.server 8765`, then open http://localhost:8765/index.html

Workspace states (3a–3i) are one component, `Workspace.dc.html`, started in different states; edit that file to change them all.

## Notes

- Fonts load from Google Fonts (Inter); offline, the system font is used. Screenshots were taken with the system font.
- Values in [brackets] are placeholders that must come from the cited clinical source.
- `support.js` is the design canvas runtime (bundles React, MIT). It is for viewing these wireframes, not for the production build.
