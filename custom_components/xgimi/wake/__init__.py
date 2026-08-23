"""Wake backends for the XGIMI integration."""

from .base import WakeBackend
from .exceptions import WakeBackendError

__all__ = ["WakeBackend", "WakeBackendError"]
