"""IdentityService: profiles, disclaimer acceptance and role checks (BR2.1-BR2.3)."""

from __future__ import annotations

import sqlite3

import pytest

from brahma.platform.errors import Forbidden, ProfileNotFound
from brahma.platform.identity import IdentityService, pack_majors


@pytest.fixture
def identity(conn: sqlite3.Connection) -> IdentityService:
    return IdentityService(conn)


def test_listed_profiles_and_sign_in_refusals(identity: IdentityService) -> None:
    assert [p.profile_id for p in identity.list_profiles()] == [
        "p-maya",
        "p-reviewer",
        "p-urologist",
    ]
    assert identity.get_profile("p-maya").demo_registration == "DEMO-REG-0001"
    with pytest.raises(ProfileNotFound):
        identity.get_profile("p-benchmark")  # unlisted system profile
    with pytest.raises(ProfileNotFound):
        identity.get_profile("p-nobody")


def test_disclaimer_needed_until_accepted(
    identity: IdentityService, conn: sqlite3.Connection
) -> None:
    assert identity.needs_disclaimer("p-maya", "1", "IBD 1.3; URO 0.1")

    acceptance_id = identity.accept_disclaimer("p-maya", "1", "IBD 1.3; URO 0.1")

    assert acceptance_id.startswith("da-")
    assert not identity.needs_disclaimer("p-maya", "1", "IBD 1.3; URO 0.1")
    entry = conn.execute("SELECT kind, profile_id, payload_json FROM pf_audit_entry").fetchone()
    assert (entry["kind"], entry["profile_id"]) == ("disclaimer_accepted", "p-maya")
    assert acceptance_id in entry["payload_json"]


def test_material_pack_changes_ask_again(identity: IdentityService) -> None:
    identity.accept_disclaimer("p-maya", "1", "IBD 1.3; URO 0.1")

    assert not identity.needs_disclaimer("p-maya", "1", "IBD 1.4; URO 0.2")  # minor bumps
    assert identity.needs_disclaimer("p-maya", "1", "IBD 2.0; URO 0.1")  # major bump
    assert identity.needs_disclaimer("p-maya", "1", "IBD 1.3; RHE 0.1; URO 0.1")  # pack added
    assert identity.needs_disclaimer("p-maya", "2", "IBD 1.3; URO 0.1")  # new disclaimer
    assert identity.needs_disclaimer("p-urologist", "1", "IBD 1.3; URO 0.1")  # other profile


def test_bad_inputs_are_refused(identity: IdentityService) -> None:
    with pytest.raises(ValueError, match=r"IBD 1\.3"):
        pack_majors("IBD v1")
    with pytest.raises(ValueError):
        identity.accept_disclaimer("p-maya", "1", "")
    with pytest.raises(ProfileNotFound):
        identity.needs_disclaimer("p-nobody", "1", "IBD 1.3")
    assert pack_majors("URO 0.1; IBD 12.3") == {"URO": 0, "IBD": 12}


def test_require_role(identity: IdentityService) -> None:
    identity.require_role("p-reviewer", "reviewer")
    identity.require_role("p-benchmark", "system")
    with pytest.raises(Forbidden):
        identity.require_role("p-maya", "reviewer")
    with pytest.raises(ProfileNotFound):
        identity.require_role("p-nobody", "doctor")
