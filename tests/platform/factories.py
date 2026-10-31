"""Typed test-data builders. Synthetic data only; each call returns a fresh model."""

from __future__ import annotations

from typing import Any

from brahma.platform.audit.models import AuditEntryIn, SessionRecordIn


def make_entry(**changes: Any) -> AuditEntryIn:
    """A valid audit entry by Dr. Maya; ``changes`` override single fields."""
    data: dict[str, Any] = {
        "kind": "case_created",
        "caseId": "case-001",
        "profileId": "p-maya",
        "packVersion": "IBD 1.3",
        "payload": {"note": "synthetic patient"},
    }
    data.update(changes)
    return AuditEntryIn.model_validate(data)


def make_session(**changes: Any) -> SessionRecordIn:
    """A valid answered session for a synthetic IBD case; ``changes`` override fields."""
    data: dict[str, Any] = {
        "caseId": "case-001",
        "walkId": "walk-001",
        "profileId": "p-maya",
        "packVersion": "IBD 1.3",
        "provider": "recorded",
        "model": "recorded",
        "inputs": {
            "text": "Bloody diarrhoea for 3 weeks, calprotectin 450 µg/g",
            "findings": [{"name": "faecal calprotectin", "value": 450, "unit": "µg/g"}],
        },
        "pathNodeIds": ["IBD-N1", "IBD-N12"],
        "answer": {
            "summary": "Ulcerative colitis, moderate (Truelove-Witts)",
            "sections": [{"id": "plan", "lines": [{"text": "Calprotectin ≥ 250", "n": 1}]}],
            "counts": {"steps": 2, "cited": 2, "ungrounded": 0},
        },
        "sources": ["IBD-S1"],
        "explanation": [{"text": "Calprotectin ≥ 250 µg/g suggests active disease"}],
        "outcome": "answered",
    }
    data.update(changes)
    return SessionRecordIn.model_validate(data)
