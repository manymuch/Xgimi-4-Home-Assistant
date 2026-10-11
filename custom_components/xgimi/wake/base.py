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
