"""Runtime data for the XGIMI integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_ESP32_WAKE_ENTITY,
    WAKE_BACKEND_AUTO,
    WAKE_BACKEND_LOCAL,
    WAKE_RESULT_SUCCESS,
)
from .pyxgimi import XgimiApi
from .repairs import async_clear_wake_repairs, async_set_wake_repair
from .wake.base import UnavailableWakeBackend, WakeBackend
from .wake.exceptions import (
    NoWakeBackendAvailableError,
    WakeBackendClosedError,
    WakeBackendError,
)
from .wake.factory import async_create_wake_backend, wake_backend_config

ConfigListener = Callable[[], None]


@dataclass(slots=True)
class XgimiRuntimeData:
    """Config-entry runtime state."""

    hass: HomeAssistant
    entry_id: str | None
    api: XgimiApi
    wake_backend: WakeBackend
    configured_wake_backend: str
    effective_wake_backend: str | None
    advertisement_duration: float
    esp32_wake_entity: str | None
    setup_wake_error: WakeBackendError | None = None
    last_wake_result: str | None = None
    last_successful_wake: datetime | None = None
    config_entry: ConfigEntry | None = None
    _backend_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _config_listeners: set[ConfigListener] = field(default_factory=set, init=False)
    _closed: bool = field(default=False, init=False)

    def add_config_listener(self, listener: ConfigListener) -> Callable[[], None]:
        """Register a callback for live configuration changes."""
        self._config_listeners.add(listener)

        def remove_listener() -> None:
            self._config_listeners.discard(listener)

        return remove_listener

    def _notify_config_listeners(self) -> None:
        """Refresh all configuration entities after a live update."""
        for listener in tuple(self._config_listeners):
            listener()

    def _update_runtime_config(
        self,
        *,
        configured_backend: str,
        effective_backend: str | None,
        advertisement_duration: float,
        esp32_wake_entity: str | None,
        setup_error: WakeBackendError | None,
    ) -> None:
        """Update the in-memory configuration and Repair state."""
        self.configured_wake_backend = configured_backend
        self.effective_wake_backend = effective_backend
        self.advertisement_duration = advertisement_duration
        self.esp32_wake_entity = esp32_wake_entity
        self.setup_wake_error = setup_error

        if self.entry_id is None:
            return
        if setup_error is None:
            async_clear_wake_repairs(self.hass, self.entry_id)
        else:
            async_set_wake_repair(self.hass, self.entry_id, setup_error)

    async def async_apply_wake_options(
        self,
        updates: Mapping[str, Any],
    ) -> WakeBackendError | None:
        """Persist and apply configuration-entity changes without a reload."""
        if self.config_entry is None:
            raise HomeAssistantError("XGIMI runtime is not linked to a config entry")
        if self._closed:
            raise HomeAssistantError("XGIMI runtime is closed")

        async with self._backend_lock:
            new_options = dict(self.config_entry.options)
            for key, value in updates.items():
                if key == CONF_ESP32_WAKE_ENTITY and not value:
                    new_options.pop(key, None)
                else:
                    new_options[key] = value

            # Persist the requested value before probing. This allows the user
            # to repair an unavailable backend from the configuration entities.
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=new_options,
            )
            config = wake_backend_config(self.config_entry)
            old_backend = self.wake_backend

            try:
                new_backend = await async_create_wake_backend(
                    self.hass,
                    self.config_entry,
                )
            except WakeBackendError as err:
                # async_create_wake_backend closes a candidate that fails its
                # probe. The old backend is also stopped so stale settings are
                # never used after a failed live update.
                with suppress(Exception):
                    await old_backend.async_close()
                self.wake_backend = UnavailableWakeBackend(
                    config.candidate_backend,
                    err,
                )
                self._update_runtime_config(
                    configured_backend=config.configured_backend,
                    effective_backend=None,
                    advertisement_duration=config.advertisement_duration,
                    esp32_wake_entity=config.esp32_entity_id,
                    setup_error=err,
                )
                self._notify_config_listeners()
                return err

            with suppress(Exception):
                await old_backend.async_close()
            self.wake_backend = new_backend
            self._update_runtime_config(
                configured_backend=config.configured_backend,
                effective_backend=new_backend.backend_type,
                advertisement_duration=config.advertisement_duration,
                esp32_wake_entity=config.esp32_entity_id,
                setup_error=None,
            )
            self._notify_config_listeners()
            return None

    async def async_wake(self) -> None:
        """Wake the projector while serializing backend replacement."""
        async with self._backend_lock:
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
        """Close the currently active backend exactly once."""
        async with self._backend_lock:
            if self._closed:
                return
            self._closed = True
            with suppress(Exception):
                await self.wake_backend.async_close()
            self._config_listeners.clear()

    def record_wake_success(self) -> None:
        """Record a successful wake and clear persistent failures."""
        self.api.mark_wake_successful()
        self.effective_wake_backend = self.wake_backend.backend_type
        self.setup_wake_error = None
        self.last_wake_result = WAKE_RESULT_SUCCESS
        self.last_successful_wake = datetime.now(UTC)
        if self.entry_id is not None:
            async_clear_wake_repairs(self.hass, self.entry_id)

    def record_wake_failure(self, error: WakeBackendError) -> None:
        """Record a failed wake without changing projector power state."""
        self.last_wake_result = error.error_code
        if self.entry_id is None:
            return

        repair_error: WakeBackendError = error
        if (
            not isinstance(error, NoWakeBackendAvailableError)
            and self.configured_wake_backend == WAKE_BACKEND_AUTO
            and not self.esp32_wake_entity
            and self.wake_backend.backend_type == WAKE_BACKEND_LOCAL
        ):
            repair_error = NoWakeBackendAvailableError(error)
            self.effective_wake_backend = None
        async_set_wake_repair(self.hass, self.entry_id, repair_error)
