"""Repair issue helpers for local Bluetooth wake failures."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import (
    DOMAIN,
    REPAIR_BLUEZ_UNAVAILABLE,
    REPAIR_CONFIGURED_ADAPTER_MISSING,
    REPAIR_DBUS_UNAVAILABLE,
    REPAIR_KEYS,
    REPAIR_NO_LOCAL_ADAPTER,
    REPAIR_WAKE_BACKEND_FAILURE,
)
from .wake.exceptions import (
    AdvertisingUnsupportedError,
    BlueZUnavailableError,
    ConfiguredAdapterMissingError,
    DBusUnavailableError,
    NoLocalAdapterError,
    WakeBackendError,
)


def _issue_id(entry_id: str, repair_key: str) -> str:
    """Return a stable per-entry issue ID."""
    return f"{entry_id}_{repair_key}"


def async_clear_wake_repairs(hass: HomeAssistant, entry_id: str) -> None:
    """Delete all local Bluetooth wake repair issues for an entry."""
    for repair_key in REPAIR_KEYS:
        ir.async_delete_issue(hass, DOMAIN, _issue_id(entry_id, repair_key))


def _repair_key_for_error(error: WakeBackendError) -> str:
    """Map a local Bluetooth exception to a repair translation key."""
    if isinstance(error, DBusUnavailableError):
        return REPAIR_DBUS_UNAVAILABLE
    if isinstance(error, BlueZUnavailableError):
        return REPAIR_BLUEZ_UNAVAILABLE
    if isinstance(error, ConfiguredAdapterMissingError):
        return REPAIR_CONFIGURED_ADAPTER_MISSING
    if isinstance(error, NoLocalAdapterError | AdvertisingUnsupportedError):
        return REPAIR_NO_LOCAL_ADAPTER
    return REPAIR_WAKE_BACKEND_FAILURE


def async_set_wake_repair(
    hass: HomeAssistant,
    entry_id: str,
    error: WakeBackendError,
) -> None:
    """Create the applicable local repair and remove stale repairs."""
    repair_key = _repair_key_for_error(error)
    for stale_key in REPAIR_KEYS:
        if stale_key != repair_key:
            ir.async_delete_issue(hass, DOMAIN, _issue_id(entry_id, stale_key))
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry_id, repair_key),
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=repair_key,
    )
