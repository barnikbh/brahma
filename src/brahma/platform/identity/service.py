"""``IdentityService``: contract C3 (profiles, disclaimer, roles).

Demo profiles only: sign-in is picking a listed profile, with no password and no other
access control claimed (BR2.1, NFR7.3).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from brahma.platform.audit.models import AuditEntryIn
from brahma.platform.audit.repository import AuditRepository
from brahma.platform.db import pf_connect, transaction
from brahma.platform.errors import Forbidden, ProfileNotFound
from brahma.platform.identity.repository import DisclaimerRepository
from brahma.platform.profiles import Profile, ProfileRepository, Role

_PACK_PART = re.compile(r"^([A-Z]{2,5}) (\d+)\.(\d+)$")


def pack_majors(pack_versions: str) -> dict[str, int]:
    """Parse ``"IBD 1.3; URO 0.1"`` into ``{"IBD": 1, "URO": 0}``.

    Raises ValueError for a string that is not in that format.
    """
    majors: dict[str, int] = {}
    for part in pack_versions.split(";"):
        match = _PACK_PART.match(part.strip())
        if match is None:
            raise ValueError(f"pack versions must look like 'IBD 1.3; URO 0.1': {part!r}")
        majors[match.group(1)] = int(match.group(2))
    return majors


class IdentityService:
    """Profiles, disclaimer acceptance and role checks."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._profiles = ProfileRepository(conn)
        self._disclaimers = DisclaimerRepository(conn)
        self._audit = AuditRepository(conn)
        self._profiles.seed()

    @classmethod
    def open(cls, path: str | Path | None = None) -> IdentityService:
        """Open ``BRAHMA_DB_PATH`` (or ``path``) with U2's connection settings."""
        return cls(pf_connect(path))

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def list_profiles(self) -> list[Profile]:
        """The three listed demo profiles; the system profile is not listed."""
        return self._profiles.list()

    def get_profile(self, profile_id: str) -> Profile:
        """A listed profile for sign-in. Raises ProfileNotFound for unknown or unlisted IDs."""
        profile = self._profiles.get(profile_id)
        if profile is None or not profile.listed:
            raise ProfileNotFound(profile_id)
        return profile

    def _require_known(self, profile_id: str) -> Profile:
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFound(profile_id)
        return profile

    def needs_disclaimer(
        self, profile_id: str, disclaimer_version: str, pack_versions: str
    ) -> bool:
        """True unless the profile accepted this disclaimer for the same packs and majors.

        A minor pack bump needs no new acceptance; a major bump or an added pack does
        (BR2.2). Raises ProfileNotFound and ValueError (malformed ``pack_versions``).
        """
        self._require_known(profile_id)
        current = pack_majors(pack_versions)
        for acceptance in self._disclaimers.list_for(profile_id, disclaimer_version):
            if pack_majors(acceptance.pack_version) == current:
                return False
        return True

    def accept_disclaimer(
        self, profile_id: str, disclaimer_version: str, pack_versions: str
    ) -> str:
        """Store the acceptance and its ``disclaimer_accepted`` audit entry in one transaction.

        Returns the acceptanceId.
        """
        self._require_known(profile_id)
        pack_majors(pack_versions)
        with transaction(self._conn):
            acceptance_id = self._disclaimers.add(profile_id, disclaimer_version, pack_versions)
            self._audit.add_entry(
                AuditEntryIn(
                    kind="disclaimer_accepted",
                    profile_id=profile_id,
                    pack_version=pack_versions,
                    payload={
                        "acceptanceId": acceptance_id,
                        "disclaimerVersion": disclaimer_version,
                    },
                )
            )
        return acceptance_id

    def require_role(self, profile_id: str, role: Role) -> None:
        """Raise Forbidden unless the profile has ``role`` (ProfileNotFound if unknown)."""
        if self._require_known(profile_id).role != role:
            raise Forbidden(profile_id, role)
