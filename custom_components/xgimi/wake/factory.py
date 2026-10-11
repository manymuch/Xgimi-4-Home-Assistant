"""Wake backend construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from ..const import (
    CONF_ADVERTISEMENT_DURATION,
    CONF_BLE_INCREMENT,
    CONF_BLUETOOTH_ADAPTER,
    CONF_DEBUG_LOGGING,
    CONF_SCAN_INTERVAL,
    CONF_WAKE_BACKEND,
    CONF_WAKE_BUTTON,
    DEFAULT_ADVERTISEMENT_DURATION,
    DEFAULT_BLE_INCREMENT,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAKE_BACKEND,
    MAX_ADVERTISEMENT_DURATION,
    MAX_SCAN_INTERVAL,
    MIN_ADVERTISEMENT_DURATION,
    MIN_SCAN_INTERVAL,
    WAKE_BACKEND_ESP32,
    WAKE_BACKEND_LOCAL,
    WAKE_BACKENDS,
)
from .base import WakeBackend
from .bluez import BlueZWakeBackend
from .esp32 import ESP32WakeBackend
from .exceptions import WakeBackendError


@dataclass(frozen=True, slots=True)
class WakeBackendConfig:
    """Normalized wake backend configuration."""

    configured_backend: str
    wake_button: str | None
    bluetooth_adapter: str | None
    advertisement_duration: float
    ble_increment: bool
    scan_interval: int
    debug_logging: bool


def _entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Read a setting from options first, then config-entry data."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


def wake_backend_config(entry: ConfigEntry) -> WakeBackendConfig:
    """Return normalized settings for the configured wake backend."""
    configured_backend = _entry_value(
        entry,
        CONF_WAKE_BACKEND,
        DEFAULT_WAKE_BACKEND,
    )
    if configured_backend not in WAKE_BACKENDS:
        configured_backend = DEFAULT_WAKE_BACKEND

    raw_duration = _entry_value(
        entry,
        CONF_ADVERTISEMENT_DURATION,
        DEFAULT_ADVERTISEMENT_DURATION,
    )
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        duration = DEFAULT_ADVERTISEMENT_DURATION
    duration = max(
        MIN_ADVERTISEMENT_DURATION,
        min(MAX_ADVERTISEMENT_DURATION, duration),
    )

    raw_button = _entry_value(entry, CONF_WAKE_BUTTON)
    wake_button = raw_button.strip() if isinstance(raw_button, str) else None

    raw_adapter = _entry_value(entry, CONF_BLUETOOTH_ADAPTER)
    bluetooth_adapter = (
        raw_adapter.strip() if isinstance(raw_adapter, str) else None
    )

    raw_increment = _entry_value(
        entry,
        CONF_BLE_INCREMENT,
        DEFAULT_BLE_INCREMENT,
    )
    raw_debug_logging = _entry_value(
        entry,
        CONF_DEBUG_LOGGING,
        DEFAULT_DEBUG_LOGGING,
    )
    raw_scan_interval = _entry_value(
        entry,
        CONF_SCAN_INTERVAL,
        DEFAULT_SCAN_INTERVAL,
    )
    try:
        scan_interval = int(raw_scan_interval)
    except (TypeError, ValueError):
        scan_interval = DEFAULT_SCAN_INTERVAL
    scan_interval = max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, scan_interval))
    return WakeBackendConfig(
        configured_backend=configured_backend,
        wake_button=wake_button or None,
        bluetooth_adapter=bluetooth_adapter or None,
        advertisement_duration=duration,
        ble_increment=(
            raw_increment
            if isinstance(raw_increment, bool)
            else DEFAULT_BLE_INCREMENT
        ),
        scan_interval=scan_interval,
        debug_logging=(
            raw_debug_logging
            if isinstance(raw_debug_logging, bool)
            else DEFAULT_DEBUG_LOGGING
        ),
    )


def create_wake_backend(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> WakeBackend:
    """Construct the configured wake backend."""
    config = wake_backend_config(entry)
    if config.configured_backend == WAKE_BACKEND_ESP32:
        return ESP32WakeBackend(
            hass,
            config.wake_button or "",
            debug_logging=config.debug_logging,
        )

    token = entry.data.get(CONF_TOKEN)
    if not isinstance(token, str) or not token:
        raise WakeBackendError(
            "A BLE token is required for the local Bluetooth wake backend."
        )
    return BlueZWakeBackend(
        token,
        adapter_path=config.bluetooth_adapter or "",
        duration=config.advertisement_duration,
        incremental=config.ble_increment,
        debug_logging=config.debug_logging,
    )
