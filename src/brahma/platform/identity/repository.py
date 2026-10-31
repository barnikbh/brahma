"""Data access for ``pf_disclaimer_acceptance`` (BR2.2)."""

from __future__ import annotations

import sqlite3

from brahma.platform.base import new_id, utc_now
from brahma.platform.identity.models import DisclaimerAcceptance


class DisclaimerRepository:
    """Stores and reads disclaimer acceptances. ``add`` runs in the caller's transaction."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, profile_id: str, disclaimer_version: str, pack_version: str) -> str:
        """Insert one acceptance and return its acceptanceId."""
        acceptance_id = new_id("da")
        self._conn.execute(
            "INSERT INTO pf_disclaimer_acceptance (acceptance_id, profile_id, "
            "disclaimer_version, pack_version, accepted_at) VALUES (?, ?, ?, ?, ?)",
            (acceptance_id, profile_id, disclaimer_version, pack_version, utc_now()),
        )
        return acceptance_id

    def list_for(self, profile_id: str, disclaimer_version: str) -> list[DisclaimerAcceptance]:
        """The profile's acceptances of this disclaimer version, oldest first."""
        rows = self._conn.execute(
            "SELECT * FROM pf_disclaimer_acceptance WHERE profile_id = ? "
            "AND disclaimer_version = ? ORDER BY accepted_at",
            (profile_id, disclaimer_version),
        )
        return [
            DisclaimerAcceptance(
                acceptance_id=r["acceptance_id"],
                profile_id=r["profile_id"],
                disclaimer_version=r["disclaimer_version"],
                pack_version=r["pack_version"],
                accepted_at=r["accepted_at"],
            )
            for r in rows
        ]
