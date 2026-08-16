"""Bluetooth diagnostic binary sensors for XGIMI projectors."""

from __future__ import annotations

from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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


class XgimiBluetoothAvailableBinarySensor(BinarySensorEntity):
    """Report availability of a local advertising-capable Bluetooth adapter."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth"
    _attr_should_poll = True

    def __init__(self, entry: ConfigEntry[XgimiRuntimeData]) -> None:
        """Initialize the Bluetooth availability sensor."""
        self._entry = entry
        self.runtime = entry.runtime_data
        self._attr_device_info = xgimi_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_bluetooth_available"
        self._attr_translation_key = "bluetooth_available"
        self._sync_from_diagnostics(self.runtime.wake_backend.diagnostics())

    def _sync_from_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        """Update the state from cached backend diagnostics."""
        self._attr_is_on = bluetooth_available(diagnostics)

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
        """Refresh local BlueZ availability without advertising."""
        diagnostics = await async_refresh_bluetooth_diagnostics(self.runtime)
        self._sync_from_diagnostics(diagnostics)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[XgimiRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the optional Bluetooth availability diagnostic entity."""
    async_add_entities([XgimiBluetoothAvailableBinarySensor(config_entry)])
