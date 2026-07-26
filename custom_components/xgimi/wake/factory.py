"""Wake backend selection and construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from ..const import (
    BLUETOOTH_ADAPTER_AUTO,
    CONF_ADVERTISEMENT_DURATION,
    CONF_BLUETOOTH_ADAPTER,
    CONF_ESP32_WAKE_ENTITY,
    CONF_WAKE_BACKEND,
    DEFAULT_ADVERTISEMENT_DURATION,
    DEFAULT_WAKE_BACKEND,
    MAX_ADVERTISEMENT_DURATION,
    MIN_ADVERTISEMENT_DURATION,
    WAKE_BACKEND_AUTO,
    WAKE_BACKEND_ESP32,
    WAKE_BACKEND_LOCAL,
    WAKE_BACKENDS,
)
from .base import WakeBackend
from .bluez import BlueZWakeBackend
from .esp32 import ESP32WakeBackend
from .exceptions import (
    NoWakeBackendAvailableError,
    WakeBackendError,
)


@dataclass(frozen=True, slots=True)
class WakeBackendConfig:
    """Normalized wake backend configuration."""

    configured_backend: str
    esp32_entity_id: str | None
    bluetooth_adapter: str
    advertisement_duration: float

    @property
    def candidate_backend(self) -> str:
        """Return the backend selected by configuration priority."""
        if self.configured_backend == WAKE_BACKEND_ESP32:
            return WAKE_BACKEND_ESP32
        if self.configured_backend == WAKE_BACKEND_LOCAL:
            return WAKE_BACKEND_LOCAL
        if self.esp32_entity_id:
            return WAKE_BACKEND_ESP32
        return WAKE_BACKEND_LOCAL


def _entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Read a new option while accepting entries that stored it in data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


def wake_backend_config(entry: ConfigEntry) -> WakeBackendConfig:
    """Return normalized backend settings for a config entry."""
    configured_backend = _entry_value(entry, CONF_WAKE_BACKEND, DEFAULT_WAKE_BACKEND)
    if configured_backend not in WAKE_BACKENDS:
        configured_backend = DEFAULT_WAKE_BACKEND

    raw_duration = _entry_value(
        entry, CONF_ADVERTISEMENT_DURATION, DEFAULT_ADVERTISEMENT_DURATION
    )
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        duration = DEFAULT_ADVERTISEMENT_DURATION
    duration = max(
        MIN_ADVERTISEMENT_DURATION,
        min(MAX_ADVERTISEMENT_DURATION, duration),
    )

    raw_entity_id = _entry_value(entry, CONF_ESP32_WAKE_ENTITY)
    entity_id = raw_entity_id.strip() if isinstance(raw_entity_id, str) else None
    return WakeBackendConfig(
        configured_backend=configured_backend,
        esp32_entity_id=entity_id or None,
        bluetooth_adapter=_entry_value(
            entry, CONF_BLUETOOTH_ADAPTER, BLUETOOTH_ADAPTER_AUTO
        ),
        advertisement_duration=duration,
    )


def create_wake_backend(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> WakeBackend:
    """Construct the configured candidate without probing it."""
    config = wake_backend_config(entry)
    if config.candidate_backend == WAKE_BACKEND_ESP32:
        return ESP32WakeBackend(hass, config.esp32_entity_id)
    return BlueZWakeBackend(
        entry.data[CONF_TOKEN],
        adapter_path=config.bluetooth_adapter,
        duration=config.advertisement_duration,
    )


async def async_create_wake_backend(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> WakeBackend:
    """Resolve, probe, and return the effective wake backend."""
    config = wake_backend_config(entry)
    backend = create_wake_backend(hass, entry)
    try:
        await backend.async_probe()
    except WakeBackendError as err:
        await backend.async_close()
        if (
            config.configured_backend == WAKE_BACKEND_AUTO
            and not config.esp32_entity_id
        ):
            raise NoWakeBackendAvailableError(err) from err
        raise
    return backend
