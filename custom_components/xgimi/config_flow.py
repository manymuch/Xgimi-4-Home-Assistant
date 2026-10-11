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
    CONF_ADVERTISEMENT_DURATION,
    CONF_ALIVE_PORT,
    CONF_BLE_INCREMENT,
    CONF_BLUETOOTH_ADAPTER,
    CONF_DEBUG_LOGGING,
    CONF_SCAN_INTERVAL,
    CONF_WAKE_BACKEND,
    CONF_WAKE_BUTTON,
    DEFAULT_ADVERTISEMENT_DURATION,
    DEFAULT_ALIVE_PORT,
    DEFAULT_BLE_INCREMENT,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WAKE_BACKEND,
    DOMAIN,
    MAX_ADVERTISEMENT_DURATION,
    MAX_MANUFACTURER_PAYLOAD_LENGTH,
    MAX_SCAN_INTERVAL,
    MIN_ADVERTISEMENT_DURATION,
    MIN_SCAN_INTERVAL,
    WAKE_BUTTON_DOMAINS,
    WAKE_BACKEND_ESP32,
    WAKE_BACKEND_LOCAL,
)
from .wake.bluez import BlueZAdapter, async_discover_bluez_adapters
from .wake.exceptions import WakeBackendError
from .wake.factory import wake_backend_config

BACKEND_OPTIONS: tuple[str, ...] = (
    WAKE_BACKEND_LOCAL,
    WAKE_BACKEND_ESP32,
)


def _backend_selector() -> selector.SelectSelector:
    """Return the explicit wake-backend selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=list(BACKEND_OPTIONS),
            mode=selector.SelectSelectorMode.DROPDOWN,
            translation_key="wake_backend",
        )
    )


def _button_selector() -> selector.EntitySelector:
    """Return a selector for any Home Assistant button entity."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=list(WAKE_BUTTON_DOMAINS),
            multiple=False,
        )
    )


def _token_is_valid(token: str) -> bool:
    """Validate a BLE token without retaining or logging its value."""
    try:
        payload = bytes.fromhex(token)
    except (TypeError, ValueError):
        return False
    return 0 < len(payload) <= MAX_MANUFACTURER_PAYLOAD_LENGTH


def _is_wake_button_entity(entity_id: Any) -> bool:
    """Return whether an entity ID uses a supported pressable domain."""
    if not isinstance(entity_id, str):
        return False
    domain, separator, object_id = entity_id.partition(".")
    return bool(separator and object_id and domain in WAKE_BUTTON_DOMAINS)


class _WakeFlowMixin:
    """Shared local-adapter discovery for config and options flows."""

    hass: Any
    _adapter_cache: list[BlueZAdapter] | None

    async def _async_adapter_options(
        self,
    ) -> list[selector.SelectOptionDict]:
        """Return concrete local advertising adapters without an auto choice."""
        if self._adapter_cache is None:
            try:
                self._adapter_cache = await async_discover_bluez_adapters()
            except WakeBackendError:
                self._adapter_cache = []

        return [
            {"value": adapter.path, "label": adapter.display_name}
            for adapter in self._adapter_cache
        ]


def _common_options() -> dict[str, Any]:
    """Return default options shared by both wake backends."""
    return {
        CONF_ALIVE_PORT: DEFAULT_ALIVE_PORT,
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_DEBUG_LOGGING: DEFAULT_DEBUG_LOGGING,
    }


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
        """Collect the projector identity and explicit wake backend."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not is_host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            if user_input.get(CONF_WAKE_BACKEND) not in BACKEND_OPTIONS:
                errors[CONF_WAKE_BACKEND] = "invalid_backend"

            if not errors:
                self._selected_backend = user_input[CONF_WAKE_BACKEND]
                self._core_data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_WAKE_BACKEND: self._selected_backend,
                }
                await self.async_set_unique_id(
                    f"{user_input[CONF_NAME]}-{user_input[CONF_HOST]}"
                )
                self._abort_if_unique_id_configured()
                if self._selected_backend == WAKE_BACKEND_LOCAL:
                    return await self.async_step_local()
                return await self.async_step_esp32()

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
                        CONF_WAKE_BACKEND,
                        default=defaults.get(
                            CONF_WAKE_BACKEND,
                            DEFAULT_WAKE_BACKEND,
                        ),
                    ): _backend_selector(),
                }
            ),
            errors=errors,
        )

    async def async_step_local(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Collect the local BLE token and concrete adapter."""
        adapter_options = await self._async_adapter_options()
        if not adapter_options:
            return self.async_abort(reason="no_local_adapter")

        errors: dict[str, str] = {}
        if user_input is not None:
            if not _token_is_valid(user_input[CONF_TOKEN]):
                errors[CONF_TOKEN] = "invalid_token"
            if user_input.get(CONF_BLUETOOTH_ADAPTER) not in {
                option["value"] for option in adapter_options
            }:
                errors[CONF_BLUETOOTH_ADAPTER] = "invalid_adapter"
            if not errors:
                data = {
                    **self._core_data,
                    CONF_TOKEN: user_input[CONF_TOKEN],
                }
                options = {
                    **_common_options(),
                    CONF_BLUETOOTH_ADAPTER: user_input[CONF_BLUETOOTH_ADAPTER],
                    CONF_ADVERTISEMENT_DURATION: DEFAULT_ADVERTISEMENT_DURATION,
                    CONF_BLE_INCREMENT: DEFAULT_BLE_INCREMENT,
                }
                return self.async_create_entry(
                    title=self._core_data[CONF_NAME],
                    data=data,
                    options=options,
                )

        defaults = user_input or {}
        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOKEN,
                        default=defaults.get(CONF_TOKEN, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_BLUETOOTH_ADAPTER,
                        default=defaults.get(
                            CONF_BLUETOOTH_ADAPTER,
                            adapter_options[0]["value"],
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=adapter_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
            last_step=True,
        )

    async def async_step_esp32(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Collect any Home Assistant button used for ESP32 wake-up."""
        errors: dict[str, str] = {}
        if user_input is not None:
            button = user_input.get(CONF_WAKE_BUTTON)
            if not _is_wake_button_entity(button):
                errors[CONF_WAKE_BUTTON] = "invalid_button"
            if not errors:
                return self.async_create_entry(
                    title=self._core_data[CONF_NAME],
                    data=self._core_data,
                    options={
                        **_common_options(),
                        CONF_WAKE_BUTTON: button,
                    },
                )

        defaults = user_input or {}
        return self.async_show_form(
            step_id="esp32",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_WAKE_BUTTON,
                        default=defaults.get(CONF_WAKE_BUTTON, vol.UNDEFINED),
                    ): _button_selector(),
                }
            ),
            errors=errors,
            last_step=True,
        )


class XgimiOptionsFlow(_WakeFlowMixin, config_entries.OptionsFlowWithReload):
    """Handle backend-specific XGIMI options."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._adapter_cache = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure common and selected-backend settings."""
        current = wake_backend_config(self.config_entry)
        schema: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_ALIVE_PORT,
                default=int(
                    self.config_entry.options.get(
                        CONF_ALIVE_PORT,
                        DEFAULT_ALIVE_PORT,
                    )
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1,
                    max=65535,
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=int(
                    self.config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    )
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=MIN_SCAN_INTERVAL,
                    max=MAX_SCAN_INTERVAL,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_DEBUG_LOGGING,
                default=current.debug_logging,
            ): selector.BooleanSelector(),
        }

        adapter_options: list[selector.SelectOptionDict] = []
        if current.configured_backend == WAKE_BACKEND_LOCAL:
            adapter_options = await self._async_adapter_options()
            if not adapter_options:
                return self.async_abort(reason="no_local_adapter")
            adapter_values = {option["value"] for option in adapter_options}
            selected_adapter = (
                current.bluetooth_adapter
                if current.bluetooth_adapter in adapter_values
                else adapter_options[0]["value"]
            )
            schema.update(
                {
                    vol.Required(
                        CONF_BLUETOOTH_ADAPTER,
                        default=selected_adapter,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=adapter_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_ADVERTISEMENT_DURATION,
                        default=current.advertisement_duration,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX,
                            min=MIN_ADVERTISEMENT_DURATION,
                            max=MAX_ADVERTISEMENT_DURATION,
                            step=1,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Required(
                        CONF_BLE_INCREMENT,
                        default=current.ble_increment,
                    ): selector.BooleanSelector(),
                }
            )
        else:
            schema[
                vol.Required(
                    CONF_WAKE_BUTTON,
                    default=current.wake_button or vol.UNDEFINED,
                )
            ] = _button_selector()

        errors: dict[str, str] = {}
        if user_input is not None:
            if current.configured_backend == WAKE_BACKEND_LOCAL:
                if user_input.get(CONF_BLUETOOTH_ADAPTER) not in {
                    option["value"] for option in adapter_options
                }:
                    errors[CONF_BLUETOOTH_ADAPTER] = "invalid_adapter"
            else:
                button = user_input.get(CONF_WAKE_BUTTON)
                if not _is_wake_button_entity(button):
                    errors[CONF_WAKE_BUTTON] = "invalid_button"
            if not errors:
                options = {
                    CONF_ALIVE_PORT: user_input[CONF_ALIVE_PORT],
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_DEBUG_LOGGING: user_input[CONF_DEBUG_LOGGING],
                }
                if current.configured_backend == WAKE_BACKEND_LOCAL:
                    options.update(
                        {
                            CONF_BLUETOOTH_ADAPTER: user_input[
                                CONF_BLUETOOTH_ADAPTER
                            ],
                            CONF_ADVERTISEMENT_DURATION: user_input[
                                CONF_ADVERTISEMENT_DURATION
                            ],
                            CONF_BLE_INCREMENT: user_input[CONF_BLE_INCREMENT],
                        }
                    )
                else:
                    options[CONF_WAKE_BUTTON] = user_input[CONF_WAKE_BUTTON]
                return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
