"""Demo profiles and the shared ``ProfileRepository`` (BR2.1).

Audit and Identity both read ``pf_profile`` through this repository, so neither module
imports the other. Profiles are synthetic demo identities; there are no passwords.
"""

from __future__ import annotations

import sqlite3
from typing import Literal

from brahma.platform.base import PfModel
from brahma.platform.db import transaction

Role = Literal["doctor", "reviewer", "system"]
BENCHMARK_PROFILE_ID = "p-benchmark"


class Profile(PfModel):
    """A seeded demo identity (contract C3). ``listed`` is false for the system profile."""

    profile_id: str
    display_name: str
    role: Role
    specialty: str | None = None
    demo_registration: str | None = None
    listed: bool = True


SEED_PROFILES = (
    Profile(
        profile_id="p-maya",
        display_name="Dr. Maya (demo)",
        role="doctor",
        specialty="gastroenterology",
        demo_registration="DEMO-REG-0001",
    ),
    Profile(
        profile_id="p-urologist",
        display_name="Demo urologist",
        role="doctor",
        specialty="urology",
        demo_registration="DEMO-REG-0002",
    ),
    Profile(
        profile_id="p-reviewer",
        display_name="Demo clinical reviewer",
        role="reviewer",
        demo_registration="DEMO-REG-0003",
    ),
    Profile(
        profile_id=BENCHMARK_PROFILE_ID,
        display_name="Benchmark runner",
        role="system",
        listed=False,
    ),
)


def _from_row(row: sqlite3.Row) -> Profile:
    return Profile(
        profile_id=row["profile_id"],
        display_name=row["display_name"],
        role=row["role"],
        specialty=row["specialty"],
        demo_registration=row["demo_registration"],
        listed=bool(row["listed"]),
    )


class ProfileRepository:
    """Reads and seeds ``pf_profile``."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def seed(self) -> None:
        """Insert the demo profiles that are missing; running it again adds nothing."""
        with transaction(self._conn):
            for p in SEED_PROFILES:
                self._conn.execute(
                    "INSERT OR IGNORE INTO pf_profile (profile_id, display_name, role, "
                    "specialty, demo_registration, listed) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        p.profile_id,
                        p.display_name,
                        p.role,
                        p.specialty,
                        p.demo_registration,
                        int(p.listed),
                    ),
                )

    def get(self, profile_id: str) -> Profile | None:
        """The profile with this ID, listed or not, or None."""
        row = self._conn.execute(
            "SELECT * FROM pf_profile WHERE profile_id = ?", (profile_id,)
        ).fetchone()
        return _from_row(row) if row is not None else None

    def list(self, *, listed_only: bool = True) -> list[Profile]:
        """Profiles ordered by ID; only listed ones unless ``listed_only`` is false."""
        sql = "SELECT * FROM pf_profile"
        if listed_only:
            sql += " WHERE listed = 1"
        return [_from_row(row) for row in self._conn.execute(sql + " ORDER BY profile_id")]
