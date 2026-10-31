"""Demo profiles, roles and the disclaimer (contract C3).

Demo profiles, no authentication: the public interface is ``IdentityService``.
"""

from brahma.platform.identity.models import DisclaimerAcceptance
from brahma.platform.identity.service import IdentityService, pack_majors
from brahma.platform.profiles import Profile, Role

__all__ = ["DisclaimerAcceptance", "IdentityService", "Profile", "Role", "pack_majors"]
