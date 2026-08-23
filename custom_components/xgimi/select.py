"""Configuration select entities for XGIMI projectors."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, override

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_FRIENDLY_NAME, MATCH_ALL
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    BLUETOOTH_ADAPTER_AUTO,
    CONF_BLUETOOTH_ADAPTER,
    CONF_ESP32_WAKE_ENTITY,
    CONF_WAKE_BACKEND,
    NO_ESP32_WAKE_ENTITY,
    WAKE_BACKENDS,
)
from .entity import xgimi_device_info
from .runtime import XgimiRuntimeData
from .wake.bluez import BlueZAdapter, async_discover_bluez_adapters
from .wake.exceptions import WakeBackendError
from .wake.factory import wake_backend_config

_UNAVAILABLE_PREFIX = "Unavailable — "


class _XgimiSelectEntity(SelectEntity):
    """Base class for live XGIMI configuration selects."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        *,
        key: str,
        translation_key: str,
    ) -> None:
        """Initialize a configuration select."""
        self._entry = entry
        self.runtime: XgimiRuntimeData = entry.runtime_data
        self._attr_device_info = xgimi_device_info(entry)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = translation_key

    async def async_added_to_hass(self) -> None:
        """Register for live runtime configuration updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.runtime.add_config_listener(self._async_runtime_updated)
        )

    @callback
    def _async_runtime_updated(self) -> None:
        """Refresh this entity after another setting changes."""
        self._sync_from_config()
        self.async_write_ha_state()

    def _sync_from_config(self) -> None:
        """Refresh options and state from the config entry."""
        raise NotImplementedError


class XgimiWakeBackendSelect(_XgimiSelectEntity):
    """Select the configured XGIMI BLE wake backend."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the backend selector."""
        super().__init__(
            entry,
            key=CONF_WAKE_BACKEND,
            translation_key="wake_backend",
        )
        self._attr_options = list(WAKE_BACKENDS)
        self._sync_from_config()

    @override
    def _sync_from_config(self) -> None:
        """Refresh the selected backend."""
        self._attr_current_option = wake_backend_config(
            self._entry
        ).configured_backend

    @override
    async def async_select_option(self, option: str) -> None:
        """Apply a new BLE wake backend."""
        if option not in WAKE_BACKENDS:
            raise HomeAssistantError(f"Unsupported XGIMI wake backend: {option}")
        await self.runtime.async_apply_wake_options({CONF_WAKE_BACKEND: option})


class XgimiEsp32WakeEntitySelect(_XgimiSelectEntity):
    """Select the Home Assistant button used for ESP32 wake."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the ESPHome button selector."""
        super().__init__(
            entry,
            key=CONF_ESP32_WAKE_ENTITY,
            translation_key="esp32_wake_entity",
        )
        self._option_to_entity_id: dict[str, str | None] = {
            NO_ESP32_WAKE_ENTITY: None
        }
        self._attr_options = [NO_ESP32_WAKE_ENTITY]
        self._sync_from_config()

    def _refresh_button_options(self) -> None:
        """Build friendly, deterministic options from button entities."""
        if self.hass is None:
            return

        states = sorted(
            self.hass.states.async_all("button"),
            key=lambda state: state.entity_id,
        )
        names: dict[str, list[str]] = defaultdict(list)
        for state in states:
            friendly_name = str(
                state.attributes.get(ATTR_FRIENDLY_NAME) or state.entity_id
            )
            names[friendly_name].append(state.entity_id)

        options = [NO_ESP32_WAKE_ENTITY]
        option_to_entity_id: dict[str, str | None] = {
            NO_ESP32_WAKE_ENTITY: None
        }
        for friendly_name in sorted(names):
            entity_ids = names[friendly_name]
            for entity_id in entity_ids:
                option = (
                    f"{friendly_name} ({entity_id})"
                    if len(entity_ids) > 1
                    else friendly_name
                )
                options.append(option)
                option_to_entity_id[option] = entity_id

        self._attr_options = options
        self._option_to_entity_id = option_to_entity_id
        self._sync_from_config()

    @override
    def _sync_from_config(self) -> None:
        """Refresh the selected ESPHome button."""
        entity_id = wake_backend_config(self._entry).esp32_entity_id
        if entity_id is None:
            self._attr_current_option = NO_ESP32_WAKE_ENTITY
            return

        current_option = next(
            (
                option
                for option, selected_entity_id in self._option_to_entity_id.items()
                if selected_entity_id == entity_id
            ),
            None,
        )
        if current_option is None:
            current_option = f"{_UNAVAILABLE_PREFIX}{entity_id}"
            if current_option not in self._attr_options:
                self._attr_options.append(current_option)
            self._option_to_entity_id[current_option] = entity_id
        self._attr_current_option = current_option

    async def async_added_to_hass(self) -> None:
        """Track button discovery and runtime configuration changes."""
        await super().async_added_to_hass()
        self._refresh_button_options()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                MATCH_ALL,
                self._async_button_state_changed,
            )
        )

    @callback
    def _async_button_state_changed(self, event: Any) -> None:
        """Refresh choices when a button entity appears or changes."""
        if not event.data["entity_id"].startswith("button."):
            return
        self._refresh_button_options()
        self.async_write_ha_state()

    @override
    async def async_select_option(self, option: str) -> None:
        """Apply the selected ESPHome button."""
        if option not in self._option_to_entity_id:
            raise HomeAssistantError(f"Unknown XGIMI wake button option: {option}")
        await self.runtime.async_apply_wake_options(
            {CONF_ESP32_WAKE_ENTITY: self._option_to_entity_id[option]}
        )


class XgimiBluetoothAdapterSelect(_XgimiSelectEntity):
    """Select the local BlueZ adapter used for BLE wake."""

    _attr_should_poll = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the Bluetooth adapter selector."""
        super().__init__(
            entry,
            key=CONF_BLUETOOTH_ADAPTER,
            translation_key="bluetooth_adapter",
        )
        self._adapter_labels: dict[str, str] = {}
        self._option_to_adapter: dict[str, str] = {
            BLUETOOTH_ADAPTER_AUTO: BLUETOOTH_ADAPTER_AUTO
        }
        self._attr_options = [BLUETOOTH_ADAPTER_AUTO]
        self._sync_from_config()

    @staticmethod
    def _unique_adapter_labels(adapters: list[BlueZAdapter]) -> dict[str, str]:
        """Return display labels keyed by stable adapter path."""
        grouped: dict[str, list[str]] = defaultdict(list)
        for adapter in adapters:
            grouped[adapter.display_name].append(adapter.path)

        labels: dict[str, str] = {}
        for display_name, paths in grouped.items():
            for path in paths:
                labels[path] = (
                    f"{display_name} ({path})" if len(paths) > 1 else display_name
                )
        return labels

    async def _async_refresh_adapters(self) -> None:
        """Discover advertising-capable adapters without breaking the entity."""
        try:
            adapters = await async_discover_bluez_adapters()
        except WakeBackendError:
            adapters = []
        self._adapter_labels = self._unique_adapter_labels(adapters)
        self._sync_from_config()

    @override
    def _sync_from_config(self) -> None:
        """Refresh the selected adapter and preserve missing selections."""
        adapter_path = wake_backend_config(self._entry).bluetooth_adapter
        self._option_to_adapter = {
            BLUETOOTH_ADAPTER_AUTO: BLUETOOTH_ADAPTER_AUTO
        }
        self._attr_options = [BLUETOOTH_ADAPTER_AUTO, *self._adapter_labels.values()]
        self._option_to_adapter.update(
            {label: path for path, label in self._adapter_labels.items()}
        )

        if adapter_path == BLUETOOTH_ADAPTER_AUTO:
            self._attr_current_option = BLUETOOTH_ADAPTER_AUTO
            return

        current_option = self._adapter_labels.get(adapter_path)
        if current_option is None:
            current_option = f"{_UNAVAILABLE_PREFIX}{adapter_path}"
            self._attr_options.append(current_option)
            self._option_to_adapter[current_option] = adapter_path
        self._attr_current_option = current_option

    @override
    async def async_added_to_hass(self) -> None:
        """Discover adapters when the entity is added."""
        await super().async_added_to_hass()
        await self._async_refresh_adapters()

    @override
    async def async_update(self) -> None:
        """Refresh the adapter list periodically."""
        await self._async_refresh_adapters()

    @override
    async def async_select_option(self, option: str) -> None:
        """Apply the selected local adapter."""
        adapter_path = self._option_to_adapter.get(option)
        if adapter_path is None:
            raise HomeAssistantError(f"Unknown XGIMI Bluetooth adapter: {option}")
        await self.runtime.async_apply_wake_options(
            {CONF_BLUETOOTH_ADAPTER: adapter_path}
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[XgimiRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up XGIMI wake configuration entities."""
    async_add_entities(
        [
            XgimiWakeBackendSelect(config_entry),
            XgimiEsp32WakeEntitySelect(config_entry),
            XgimiBluetoothAdapterSelect(config_entry),
        ]
    )
