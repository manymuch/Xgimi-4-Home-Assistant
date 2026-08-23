"""Configuration number entities for XGIMI projectors."""

from __future__ import annotations

from typing import override

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ADVERTISEMENT_DURATION,
    MAX_ADVERTISEMENT_DURATION,
    MIN_ADVERTISEMENT_DURATION,
)
from .entity import xgimi_device_info
from .runtime import XgimiRuntimeData
from .wake.factory import wake_backend_config


class XgimiAdvertisementDurationNumber(NumberEntity):
    """Set how long a local BLE wake advertisement remains active."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_ADVERTISEMENT_DURATION
    _attr_native_max_value = MAX_ADVERTISEMENT_DURATION
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the duration number entity."""
        self._entry = entry
        self.runtime: XgimiRuntimeData = entry.runtime_data
        self._attr_device_info = xgimi_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_{CONF_ADVERTISEMENT_DURATION}"
        self._attr_translation_key = "advertisement_duration"
        self._sync_from_config()

    async def async_added_to_hass(self) -> None:
        """Register for live runtime configuration updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.runtime.add_config_listener(self._async_runtime_updated)
        )

    def _sync_from_config(self) -> None:
        """Refresh the duration from normalized entry options."""
        self._attr_native_value = wake_backend_config(
            self._entry
        ).advertisement_duration

    def _async_runtime_updated(self) -> None:
        """Refresh state after another configuration entity changes."""
        self._sync_from_config()
        self.async_write_ha_state()

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Persist and apply a new advertisement duration."""
        if not MIN_ADVERTISEMENT_DURATION <= value <= MAX_ADVERTISEMENT_DURATION:
            raise HomeAssistantError("XGIMI advertisement duration is out of range")
        await self.runtime.async_apply_wake_options(
            {CONF_ADVERTISEMENT_DURATION: value}
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[XgimiRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the XGIMI advertisement-duration entity."""
    async_add_entities([XgimiAdvertisementDurationNumber(config_entry)])
