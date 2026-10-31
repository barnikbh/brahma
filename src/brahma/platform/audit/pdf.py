"""Readable PDF export of one session (BR1.4, NFR6.2).

Uses fpdf2's built-in Helvetica (no bundled font, by the person's decision), so all
text is first made Latin-1 safe: clinical symbols map to ASCII (``≥`` to ``>=``), µ and
the middle dot stay (both are Latin-1), and any other character becomes ``?``.
Every page header reads "Decision support, not diagnosis · Synthetic patient".
"""

from __future__ import annotations

import json
from typing import Any

from fpdf import FPDF

from brahma.platform.audit.models import SessionDetail
from brahma.platform.errors import ExportFailed

HEADER = "Decision support, not diagnosis · Synthetic patient"
_REPLACEMENTS = {
    "≥": ">=",
    "≤": "<=",
    "✓": "OK",
    "✕": "x",
    "◐": "partial",
    "⊘": "n/a",
    "→": "->",
}


def to_latin1_safe(text: str) -> str:
    """Map known symbols to ASCII and any other non-Latin-1 character to ``?``."""
    out: list[str] = []
    for char in text:
        if char in _REPLACEMENTS:
            out.append(_REPLACEMENTS[char])
        elif ord(char) <= 0xFF:
            out.append(char)
        else:
            out.append("?")
    return "".join(out)


class _SessionPdf(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, to_latin1_safe(HEADER), new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


class PdfExporter:
    """Renders a ``SessionDetail`` as PDF bytes, or raises ``ExportFailed``."""

    def render(self, detail: SessionDetail) -> bytes:
        """Return the whole PDF; any failure raises ExportFailed and returns nothing."""
        try:
            return self._render(detail)
        except Exception as exc:
            raise ExportFailed(f"PDF export failed: {type(exc).__name__}") from exc

    def _render(self, detail: SessionDetail) -> bytes:
        record = detail.record
        pdf = _SessionPdf()
        pdf.add_page()
        sections: list[tuple[str, list[str]]] = [
            (
                "Session",
                [
                    f"Session: {record.session_id}",
                    f"Case: {record.case_id}",
                    f"Profile: {record.profile_id}",
                    f"Pack version: {record.pack_version}",
                    f"Provider: {record.provider} / {record.model}",
                    f"Outcome: {record.outcome}",
                    f"Recorded: {record.created_at}",
                ],
            ),
            ("Inputs", [record.inputs.text, *map(_as_text, record.inputs.findings)]),
            ("Path", [" -> ".join(record.path_node_ids)]),
            ("Answer", [record.answer.summary, *map(_as_text, record.answer.sections)]),
            ("Sources", list(record.sources)),
            ("Why", [_as_text(item) for item in record.explanation]),
            (
                "Audit entries",
                [f"{e.created_at}  {e.kind}  {e.profile_id}" for e in detail.entries],
            ),
        ]
        for title, lines in sections:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, to_latin1_safe(title), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for line in lines:
                pdf.multi_cell(0, 5, to_latin1_safe(line), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        return bytes(pdf.output())
