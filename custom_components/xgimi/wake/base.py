"""Common wake backend interfaces."""

from __future__ import annotations

from typing import Any, Protocol


class WakeBackend(Protocol):
    """Interface implemented by projector wake backends."""

    backend_type: str

    async def async_probe(self) -> None:
        """Verify that the backend is available."""

    async def async_wake(self) -> None:
        """Wake the projector."""

    async def async_close(self) -> None:
        """Release backend resources."""

    def diagnostics(self) -> dict[str, Any]:
        """Return non-sensitive cached backend diagnostics."""


class UnavailableWakeBackend:
    """Backend used when configuration cannot construct a wake backend."""

    def __init__(self, backend_type: str, error: Exception) -> None:
        """Initialize an unavailable backend."""
        self.backend_type = backend_type
        self._error = error

    async def async_probe(self) -> None:
        """Raise the construction error."""
        raise self._error

    async def async_wake(self) -> None:
        """Raise the construction error."""
        raise self._error

    async def async_close(self) -> None:
        """Release resources."""

    def diagnostics(self) -> dict[str, Any]:
        """Return safe diagnostics."""
        error_code = getattr(self._error, "error_code", "wake_backend_error")
        return {"backend_available": False, "backend_error": error_code}
