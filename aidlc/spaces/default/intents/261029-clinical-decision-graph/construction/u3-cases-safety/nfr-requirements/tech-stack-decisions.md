# Tech Stack Decisions — u3-cases-safety

Upstream: `functional-spec.md` (U3), `requirements.md` (NFR9, NFR12), `contract-summary.md` (C5).

The U3 stack is the same as U1 and U2. It adds no new dependencies.

- **Language and environment:** Python 3.12+, with Pydantic v2 models for C5 types.
- **Storage:** SQLite (WAL) in the shared file, with tables prefixed `cs_`.
- **Rounding:** `Decimal` for dose arithmetic, using U1's unit table for conversions.
- **Quality:** pytest with 80% coverage for `brahma.cases`, `mypy --strict` and Ruff (NFR9, NFR12).
- **Performance:** a target of under 50 ms per call on the demo data. A dose or safety call reads only the case's drug and safety nodes (NFR1 budget).
