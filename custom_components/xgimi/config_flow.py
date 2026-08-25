"""Config and options flows for the XGIMI integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util.network import is_host_valid

from .const import (
    BLUETOOTH_ADAPTER_AUTO,
    CONF_ADVERTISEMENT_DURATION,
    CONF_ALIVE_PORT,
    CONF_BLUETOOTH_ADAPTER,
    CONF_DEBUG_LOGGING,
    CONF_ESP32_WAKE_ENTITY,
    CONF_WAKE_BACKEND,
    DEFAULT_ADVERTISEMENT_DURATION,
    DEFAULT_ALIVE_PORT,
    DEFAULT_WAKE_BACKEND,
    DOMAIN,
    ESP32_WAKE_ENTITY_DOMAIN,
    MAX_MANUFACTURER_PAYLOAD_LENGTH,
    WAKE_BACKEND_AUTO,
    WAKE_BACKEND_ESP32,
    WAKE_BACKEND_LOCAL,
)
from .wake.bluez import BlueZAdapter, async_discover_bluez_adapters
from .wake.exceptions import WakeBackendError
from .wake.factory import wake_backend_config

BACKEND_OPTIONS: list[str] = [
    WAKE_BACKEND_AUTO,
    WAKE_BACKEND_LOCAL,
    WAKE_BACKEND_ESP32,
]


def _backend_selector() -> selector.SelectSelector:
    """Return the wake-backend selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=BACKEND_OPTIONS,
            mode=selector.SelectSelectorMode.DROPDOWN,
            translation_key="wake_backend",
        )
    )


def _entity_marker(current: str | None, *, required: bool) -> vol.Marker:
    """Return a required or optional entity schema marker."""
    if required:
        return vol.Required(
            CONF_ESP32_WAKE_ENTITY,
            default=current if current is not None else vol.UNDEFINED,
        )
    if current is not None:
        return vol.Optional(CONF_ESP32_WAKE_ENTITY, default=current)
    return vol.Optional(CONF_ESP32_WAKE_ENTITY)


def _entity_selector() -> selector.EntitySelector:
    """Return a button-only entity selector."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=ESP32_WAKE_ENTITY_DOMAIN,
            multiple=False,
        )
    )


def _token_is_valid(token: str) -> bool:
    """Validate a token without retaining or logging its decoded value."""
    try:
        payload = bytes.fromhex(token)
    except (TypeError, ValueError):
        return False
    return 0 < len(payload) <= MAX_MANUFACTURER_PAYLOAD_LENGTH


def _validate_entity_exists(
    flow: config_entries.ConfigFlow | config_entries.OptionsFlow,
    user_input: dict[str, Any],
    errors: dict[str, str],
) -> None:
    """Validate an optional configured wake entity."""
    entity_id = user_input.get(CONF_ESP32_WAKE_ENTITY)
    if entity_id:
        if not entity_id.startswith(f"{ESP32_WAKE_ENTITY_DOMAIN}."):
            errors[CONF_ESP32_WAKE_ENTITY] = "entity_unsupported"
        elif flow.hass.states.get(entity_id) is None:
            errors[CONF_ESP32_WAKE_ENTITY] = "entity_missing"


class _WakeFlowMixin:
    """Shared conditional wake configuration steps."""

    hass: Any
    _selected_backend: str
    _adapter_cache: list[BlueZAdapter] | None

    async def _async_adapter_options(self) -> list[selector.SelectOptionDict]:
        """Return currently available local advertising adapters."""
        if self._adapter_cache is None:
            try:
                self._adapter_cache = await async_discover_bluez_adapters()
            except WakeBackendError:
                self._adapter_cache = []
        return [
            {"value": BLUETOOTH_ADAPTER_AUTO, "label": "Automatic"},
            *[
                {"value": adapter.path, "label": adapter.display_name}
                for adapter in self._adapter_cache
            ],
        ]

    async def _async_wake_schema(
        self,
        backend: str,
        current: dict[str, Any],
    ) -> vol.Schema:
        """Build the conditional wake options schema."""
        schema: dict[vol.Marker, Any] = {}
        if backend in (WAKE_BACKEND_AUTO, WAKE_BACKEND_ESP32):
            schema[
                _entity_marker(
                    current.get(CONF_ESP32_WAKE_ENTITY),
                    required=backend == WAKE_BACKEND_ESP32,
                )
            ] = _entity_selector()
        if backend in (WAKE_BACKEND_AUTO, WAKE_BACKEND_LOCAL):
            adapter_options = await self._async_adapter_options()
            selected_adapter = current.get(
                CONF_BLUETOOTH_ADAPTER, BLUETOOTH_ADAPTER_AUTO
            )
            if not any(
                option["value"] == selected_adapter for option in adapter_options
            ):
                adapter_options.append(
                    {
                        "value": selected_adapter,
                        "label": f"Unavailable — {selected_adapter}",
                    }
                )
            schema[vol.Required(CONF_BLUETOOTH_ADAPTER, default=selected_adapter)] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=adapter_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            )
        return vol.Schema(schema)


class XgimiConfigFlow(
    _WakeFlowMixin,
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle XGIMI config flows."""

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._core_data: dict[str, Any] = {}
        self._selected_backend = DEFAULT_WAKE_BACKEND
        self._adapter_cache = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> XgimiOptionsFlow:
        """Return the options flow."""
        return XgimiOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Collect projector details and the initial wake mode."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not is_host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            if not _token_is_valid(user_input[CONF_TOKEN]):
                errors[CONF_TOKEN] = "invalid_token"
            if not errors:
                entry_data = dict(user_input)
                await self.async_set_unique_id(
                    f"{entry_data[CONF_NAME]}-{entry_data[CONF_TOKEN]}"
                )
                self._abort_if_unique_id_configured()
                self._selected_backend = entry_data.pop(CONF_WAKE_BACKEND)
                self._core_data = entry_data
                return await getattr(self, f"async_step_{self._selected_backend}")()

        defaults = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=defaults.get(CONF_NAME, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_HOST,
                        default=defaults.get(CONF_HOST, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_TOKEN,
                        default=defaults.get(CONF_TOKEN, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_WAKE_BACKEND,
                        default=defaults.get(CONF_WAKE_BACKEND, DEFAULT_WAKE_BACKEND),
                    ): _backend_selector(),
                }
            ),
            errors=errors,
        )

    async def _async_finish_wake_step(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Validate a wake step and create the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            _validate_entity_exists(self, user_input, errors)
            if not errors:
                options = {
                    CONF_WAKE_BACKEND: self._selected_backend,
                    **user_input,
                }
                options.setdefault(
                    CONF_ADVERTISEMENT_DURATION,
                    DEFAULT_ADVERTISEMENT_DURATION,
                )
                options.setdefault(CONF_ALIVE_PORT, DEFAULT_ALIVE_PORT)
                return self.async_create_entry(
                    title=self._core_data[CONF_NAME],
                    data=self._core_data,
                    options=options,
                )
        return self.async_show_form(
            step_id=step_id,
            data_schema=await self._async_wake_schema(
                self._selected_backend, user_input or {}
            ),
            errors=errors,
            last_step=True,
        )

    async def async_step_auto(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure automatic wake selection."""
        return await self._async_finish_wake_step(WAKE_BACKEND_AUTO, user_input)

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure local Bluetooth wake."""
        return await self._async_finish_wake_step(WAKE_BACKEND_LOCAL, user_input)

    async def async_step_esp32(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure ESP32 wake."""
        return await self._async_finish_wake_step(WAKE_BACKEND_ESP32, user_input)


class XgimiOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle integration-level XGIMI options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure integration-level diagnostics."""
        current = wake_backend_config(self.config_entry)
        current_alive_port = int(
            self.config_entry.options.get(CONF_ALIVE_PORT, DEFAULT_ALIVE_PORT)
        )
        if user_input is not None:
            options = dict(self.config_entry.options)
            options.setdefault(CONF_WAKE_BACKEND, current.configured_backend)
            if current.esp32_entity_id is not None:
                options.setdefault(CONF_ESP32_WAKE_ENTITY, current.esp32_entity_id)
            options.setdefault(CONF_BLUETOOTH_ADAPTER, current.bluetooth_adapter)
            options.setdefault(
                CONF_ADVERTISEMENT_DURATION,
                current.advertisement_duration,
            )
            options[CONF_ALIVE_PORT] = user_input[CONF_ALIVE_PORT]
            options[CONF_DEBUG_LOGGING] = user_input[CONF_DEBUG_LOGGING]
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ALIVE_PORT,
                        default=current_alive_port,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX,
                            min=1,
                            max=65535,
                        )
                    ),
                    vol.Optional(
                        CONF_DEBUG_LOGGING,
                        default=current.debug_logging,
                    ): selector.BooleanSelector(),
                }
            ),
        )
