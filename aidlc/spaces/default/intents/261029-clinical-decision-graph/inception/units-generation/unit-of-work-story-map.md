# Unit-to-Story Map — Brahma

Upstream: `stories.md` (US1.1–US9.1), `unit-of-work.md` (U1–U8), `components.md`. A story names every unit that implements part of it; each named unit traces that story's acceptance criteria in its Functional Design.

| Story | Unit IDs | Directories |
|---|---|---|
| US1.1 | U2; U8 | u2-platform; u8-web-app |
| US1.2 | U2; U8 | u2-platform; u8-web-app |
| US2.1 | U3; U8 | u3-cases-safety; u8-web-app |
| US3.1 | U4; U3; U8 | u4-grounded-agent; u3-cases-safety; u8-web-app |
| US3.2 | U4; U1; U8 | u4-grounded-agent; u1-knowledge-graph; u8-web-app |
| US3.3 | U4; U8 | u4-grounded-agent; u8-web-app |
| US3.4 | U4; U2; U8 | u4-grounded-agent; u2-platform; u8-web-app |
| US3.5 | U8; U4 | u8-web-app; u4-grounded-agent |
| US3.6 | U4; U1; U8 | u4-grounded-agent; u1-knowledge-graph; u8-web-app |
| US4.1 | U3; U8 | u3-cases-safety; u8-web-app |
| US4.2 | U3; U8 | u3-cases-safety; u8-web-app |
| US5.1 | U6; U8 | u6-prescriptions-followup; u8-web-app |
| US6.1 | U6; U8 | u6-prescriptions-followup; u8-web-app |
| US7.1 | U2; U4 | u2-platform; u4-grounded-agent |
| US7.2 | U2; U8 | u2-platform; u8-web-app |
| US8.1 | U5; U8 | u5-knowledge-updates; u8-web-app |
| US8.2 | U5; U1; U8 | u5-knowledge-updates; u1-knowledge-graph; u8-web-app |
| US8.3 | U5 | u5-knowledge-updates |
| US9.1 | U1; U4 | u1-knowledge-graph; u4-grounded-agent |

## Cross-cutting Rows

- **US3.1, US3.2:** the demo walk spans the agent (U4), the case record (U3), the content (U1) and the screens (U8).
- **US3.4:** provider errors start in the gateway (U2) and are shown by the workspace (U8).
- **US7.1:** U4 writes the session record and U2 stores it append-only.

## Implementation Order Within Each Unit

| Unit | Order |
|---|---|
| U1 | Graph model and loader → UC branch content → Crohn's content → safety and response-criterion nodes → urology stub |
| U2 | Audit (append-only) → profiles and disclaimer → model gateway |
| U3 | Patients and cases → findings and validation → version pin and tab lock → dose and safety → treatment edits |
| U4 | Grounding guard → walk and pathway → needs-more-data and out-of-knowledge → streaming server → why → explore and re-walk |
| U5 | Proposals and publish → source fetch and copy flag → drafting → scheduler |
| U6 | Prescription draft and checks → sign, PDF and void → follow-up visits → verdicts and trends |
| U7 | Case set → graph and plain runs → scoring and pass → resume |
| U8 | Shell and sign-in → Patients → workspace and chat → map → node panel → History → Knowledge → Benchmark → prescription and follow-up |

## Coverage Verification

- All 19 stories are assigned to at least one unit.
- Every unit has at least one story: U1 (US3.2, US3.6, US8.2, US9.1), U2 (US1.1, US1.2, US3.4, US7.1, US7.2), U3 (US2.1, US3.1, US4.1, US4.2), U4 (US3.1–US3.6, US7.1, US9.1), U5 (US8.1–US8.3), U6 (US5.1, US6.1), U7 (none: the benchmark is requirements-only, FR13), U8 (17 stories).
- U7 implements FR13 directly. It has no story because you chose no judge persona (user-stories Q3).
