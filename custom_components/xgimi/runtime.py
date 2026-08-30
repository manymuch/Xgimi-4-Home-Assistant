"""Runtime data for the XGIMI integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant

from .const import WAKE_BACKEND_LOCAL, WAKE_RESULT_SUCCESS
from .pyxgimi import XgimiApi
from .repairs import async_clear_wake_repairs, async_set_wake_repair
from .wake.base import WakeBackend
from .wake.exceptions import WakeBackendClosedError, WakeBackendError


@dataclass(slots=True)
class XgimiRuntimeData:
    """Config-entry runtime state."""

    hass: HomeAssistant
    entry_id: str
    api: XgimiApi
    wake_backend: WakeBackend
    configured_wake_backend: str
    wake_button: str | None
    advertisement_duration: float
    scan_interval: int
    debug_logging: bool
    setup_wake_error: WakeBackendError | None = None
    last_wake_result: str | None = None
    last_successful_wake: datetime | None = None
    _wake_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _closed: bool = field(default=False, init=False)

    async def async_wake(self) -> None:
        """Wake the projector through the selected backend."""
        async with self._wake_lock:
            if self._closed:
                raise WakeBackendClosedError
            try:
                await self.wake_backend.async_wake()
            except asyncio.CancelledError:
                raise
            except WakeBackendError as err:
                self.record_wake_failure(err)
                raise
            except Exception as err:
                safe_error = WakeBackendError()
                self.record_wake_failure(safe_error)
                raise safe_error from err

            self.record_wake_success()

    async def async_close(self) -> None:
        """Close the wake backend exactly once."""
        async with self._wake_lock:
            if self._closed:
                return
            self._closed = True
            with suppress(Exception):
                await self.wake_backend.async_close()

    def record_wake_success(self) -> None:
        """Record a successful wake and clear local Bluetooth repairs."""
        self.api.mark_wake_successful()
        self.setup_wake_error = None
        self.last_wake_result = WAKE_RESULT_SUCCESS
        self.last_successful_wake = datetime.now(UTC)
        if self.configured_wake_backend == WAKE_BACKEND_LOCAL:
            async_clear_wake_repairs(self.hass, self.entry_id)

    def record_wake_failure(self, error: WakeBackendError) -> None:
        """Record a wake failure and repair only local Bluetooth problems."""
        self.last_wake_result = error.error_code
        if self.configured_wake_backend == WAKE_BACKEND_LOCAL:
            async_set_wake_repair(self.hass, self.entry_id, error)
