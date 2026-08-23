"""Repair issue helpers for XGIMI wake backends."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import (
    DOMAIN,
    REPAIR_BLUEZ_UNAVAILABLE,
    REPAIR_CONFIGURED_ADAPTER_MISSING,
    REPAIR_DBUS_UNAVAILABLE,
    REPAIR_ESP32_ENTITY_MISSING,
    REPAIR_ESP32_ENTITY_UNAVAILABLE,
    REPAIR_KEYS,
    REPAIR_NO_BACKEND_AVAILABLE,
    REPAIR_NO_LOCAL_ADAPTER,
    REPAIR_WAKE_BACKEND_FAILURE,
)
from .wake.exceptions import (
    AdvertisingUnsupportedError,
    BlueZUnavailableError,
    ConfiguredAdapterMissingError,
    DBusUnavailableError,
    ESP32WakeEntityMissingError,
    ESP32WakeEntityUnavailableError,
    NoLocalAdapterError,
    NoWakeBackendAvailableError,
    WakeBackendError,
)


def _issue_id(entry_id: str, repair_key: str) -> str:
    """Return a stable per-entry issue ID."""
    return f"{entry_id}_{repair_key}"


def async_clear_wake_repairs(hass: HomeAssistant, entry_id: str) -> None:
    """Delete all wake-related repair issues for an entry."""
    for repair_key in REPAIR_KEYS:
        ir.async_delete_issue(hass, DOMAIN, _issue_id(entry_id, repair_key))


def _repair_key_for_error(error: WakeBackendError) -> str:
    """Map a wake exception to a repair translation key."""
    if isinstance(error, NoWakeBackendAvailableError):
        return REPAIR_NO_BACKEND_AVAILABLE
    if isinstance(error, DBusUnavailableError):
        return REPAIR_DBUS_UNAVAILABLE
    if isinstance(error, BlueZUnavailableError):
        return REPAIR_BLUEZ_UNAVAILABLE
    if isinstance(error, ConfiguredAdapterMissingError):
        return REPAIR_CONFIGURED_ADAPTER_MISSING
    if isinstance(error, NoLocalAdapterError | AdvertisingUnsupportedError):
        return REPAIR_NO_LOCAL_ADAPTER
    if isinstance(error, ESP32WakeEntityMissingError):
        return REPAIR_ESP32_ENTITY_MISSING
    if isinstance(error, ESP32WakeEntityUnavailableError):
        return REPAIR_ESP32_ENTITY_UNAVAILABLE
    return REPAIR_WAKE_BACKEND_FAILURE


def _repair_keys_for_error(error: WakeBackendError) -> set[str]:
    """Return all actionable Repair keys for an error."""
    keys = {_repair_key_for_error(error)}
    if isinstance(error, NoWakeBackendAvailableError) and error.cause is not None:
        cause_key = _repair_key_for_error(error.cause)
        if cause_key != REPAIR_WAKE_BACKEND_FAILURE:
            keys.add(cause_key)
    return keys


def async_set_wake_repair(
    hass: HomeAssistant,
    entry_id: str,
    error: WakeBackendError,
) -> None:
    """Create the applicable Repair and remove stale wake Repairs."""
    repair_keys = _repair_keys_for_error(error)
    for stale_key in REPAIR_KEYS:
        if stale_key not in repair_keys:
            ir.async_delete_issue(hass, DOMAIN, _issue_id(entry_id, stale_key))
    for repair_key in repair_keys:
        ir.async_create_issue(
            hass,
            DOMAIN,
            _issue_id(entry_id, repair_key),
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key=repair_key,
        )
