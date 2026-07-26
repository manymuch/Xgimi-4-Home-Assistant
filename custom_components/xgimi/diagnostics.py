"""Diagnostics for the XGIMI integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .runtime import XgimiRuntimeData


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry[XgimiRuntimeData],
) -> dict[str, Any]:
    """Return non-sensitive diagnostics for a config entry."""
    runtime = entry.runtime_data
    backend_diagnostics = runtime.wake_backend.diagnostics()
    last_success = runtime.last_successful_wake

    return {
        "configured_wake_backend": runtime.configured_wake_backend,
        "effective_wake_backend": runtime.effective_wake_backend,
        "supported_commands": list(runtime.api.supported_commands),
        "esp32_wake_entity": runtime.esp32_wake_entity,
        "esp32_entity_available": backend_diagnostics.get("esp32_entity_available"),
        "dbus_available": backend_diagnostics.get("dbus_available"),
        "bluez_available": backend_diagnostics.get("bluez_available"),
        "selected_adapter": backend_diagnostics.get("selected_adapter"),
        "advertising_supported": backend_diagnostics.get("advertising_supported"),
        "supported_instances": backend_diagnostics.get("supported_instances"),
        "active_instances": backend_diagnostics.get("active_instances"),
        "advertisement_duration": runtime.advertisement_duration,
        "last_wake_result": runtime.last_wake_result,
        "last_successful_wake": (
            last_success.isoformat() if last_success is not None else None
        ),
        "projector_reachable": runtime.api.projector_reachable,
        "setup_wake_error": (
            runtime.setup_wake_error.error_code
            if runtime.setup_wake_error is not None
            else None
        ),
    }
