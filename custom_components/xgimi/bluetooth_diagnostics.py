"""Shared helpers for optional XGIMI Bluetooth diagnostic entities."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_TOKEN

from .runtime import XgimiRuntimeData
from .wake.bluez import BlueZWakeBackend
from .wake.exceptions import WakeBackendError
from .wake.factory import wake_backend_config


def bluetooth_available(diagnostics: dict[str, Any]) -> bool | None:
    """Return whether a local advertising-capable Bluetooth adapter is available."""
    if "dbus_available" not in diagnostics:
        return None
    return bool(
        diagnostics.get("dbus_available")
        and diagnostics.get("bluez_available")
        and diagnostics.get("selected_adapter")
    )


async def async_refresh_bluetooth_diagnostics(
    runtime: XgimiRuntimeData,
) -> dict[str, Any]:
    """Refresh local BlueZ diagnostics without creating an advertisement."""
    backend = runtime.wake_backend
    probe_backend = backend
    temporary_backend = False

    if not isinstance(backend, BlueZWakeBackend):
        entry = runtime.config_entry
        if entry is None or CONF_TOKEN not in entry.data:
            return backend.diagnostics()
        config = wake_backend_config(entry)
        probe_backend = BlueZWakeBackend(
            entry.data[CONF_TOKEN],
            adapter_path=config.bluetooth_adapter,
            duration=config.advertisement_duration,
            debug_logging=runtime.debug_logging,
        )
        temporary_backend = True

    try:
        try:
            await probe_backend.async_probe()
        except WakeBackendError:
            pass
        return probe_backend.diagnostics()
    finally:
        if temporary_backend:
            await probe_backend.async_close()
