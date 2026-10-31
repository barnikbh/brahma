"""The model gateway (contract C4).

The public interface is ``ModelGateway`` (``current``, ``complete``) plus the request
and response models. The provider is chosen by environment configuration only.
"""

from brahma.platform.models.config import ProviderConfig
from brahma.platform.models.gateway import ModelGateway
from brahma.platform.models.schemas import CurrentModel, ModelRequest, ModelResponse, Purpose

__all__ = [
    "CurrentModel",
    "ModelGateway",
    "ModelRequest",
    "ModelResponse",
    "ProviderConfig",
    "Purpose",
]
