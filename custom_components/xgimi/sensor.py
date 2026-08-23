"""Bluetooth diagnostic sensors for XGIMI projectors."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bluetooth_diagnostics import (
    async_refresh_bluetooth_diagnostics,
    bluetooth_available,
)
from .entity import xgimi_device_info
from .runtime import XgimiRuntimeData


class XgimiBluetoothDiagnosticsSensor(SensorEntity):
    """Expose cached Bluetooth and BlueZ diagnostics as entity attributes."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-settings"
    _attr_should_poll = True

    def __init__(self, entry: ConfigEntry[XgimiRuntimeData]) -> None:
        """Initialize the Bluetooth diagnostics sensor."""
        self._entry = entry
        self.runtime = entry.runtime_data
        self._attr_device_info = xgimi_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_bluetooth_diagnostics"
        self._attr_translation_key = "bluetooth_diagnostics"
        self._sync_from_diagnostics(self.runtime.wake_backend.diagnostics())

    def _sync_from_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        """Update the state and attributes from backend diagnostics."""
        selected_adapter = diagnostics.get("selected_adapter")
        self._attr_native_value = selected_adapter
        self._attr_extra_state_attributes = {
            "bluetooth_available": bluetooth_available(diagnostics),
            "debug_logging": diagnostics.get("debug_logging", False),
            "dbus_available": diagnostics.get("dbus_available"),
            "bluez_available": diagnostics.get("bluez_available"),
            "advertising_supported": diagnostics.get("advertising_supported"),
            "supported_instances": diagnostics.get("supported_instances"),
            "active_instances": diagnostics.get("active_instances"),
            "bluez_version": diagnostics.get("bluez_version"),
            "supported_features": diagnostics.get("supported_features"),
            "supported_includes": diagnostics.get("supported_includes"),
            "controller_capabilities": diagnostics.get("supported_capabilities"),
        }

    async def async_added_to_hass(self) -> None:
        """Refresh after backend replacement or configuration changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.runtime.add_config_listener(self._async_runtime_updated)
        )

    @callback
    def _async_runtime_updated(self) -> None:
        """Refresh after the wake backend changes."""
        self._sync_from_diagnostics(self.runtime.wake_backend.diagnostics())
        self.async_write_ha_state()

    @override
    async def async_update(self) -> None:
        """Refresh local Bluetooth diagnostics without advertising."""
        diagnostics = await async_refresh_bluetooth_diagnostics(self.runtime)
        self._sync_from_diagnostics(diagnostics)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[XgimiRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the optional Bluetooth diagnostics entity."""
    async_add_entities([XgimiBluetoothDiagnosticsSensor(config_entry)])
