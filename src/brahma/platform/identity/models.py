"""Identity models (entities.md DisclaimerAcceptance)."""

from __future__ import annotations

from brahma.platform.base import PfModel


class DisclaimerAcceptance(PfModel):
    """A profile's acceptance of a disclaimer version for a pack-versions string."""

    acceptance_id: str
    profile_id: str
    disclaimer_version: str
    pack_version: str
    accepted_at: str
