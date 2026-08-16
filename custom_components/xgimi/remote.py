"""Remote entity for XGIMI projectors."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COMMAND_POWER_OFF, COMMAND_POWER_ON
from .entity import xgimi_device_info
from .runtime import XgimiRuntimeData
from .wake.exceptions import WakeBackendError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[XgimiRuntimeData],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up an XGIMI remote from a config entry."""
    unique_id = config_entry.unique_id
    assert unique_id is not None
    async_add_entities(
        [
            XgimiRemote(
                config_entry.runtime_data,
                config_entry.data[CONF_NAME],
                unique_id,
                device_info=xgimi_device_info(config_entry),
            )
        ]
    )


class XgimiRemote(RemoteEntity):
    """Representation of an XGIMI projector remote."""

    _attr_icon = "mdi:projector"

    def __init__(
        self,
        runtime: XgimiRuntimeData,
        name: str,
        unique_id: str,
        *,
        device_info: Any | None = None,
    ) -> None:
        """Initialize the remote entity."""
        self.runtime = runtime
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool:
        """Return whether the projector is on."""
        return self.runtime.api.is_on

    @property
    def supported_commands(self) -> tuple[str, ...]:
        """Return the command names accepted by the remote."""
        return self.runtime.api.supported_commands

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """Return read-only command metadata for automations and diagnostics."""
        return {"supported_commands": list(self.supported_commands)}

    async def async_update(self) -> None:
        """Retrieve the latest projector state."""
        await self.runtime.api.async_fetch_data()

    async def _async_wake(self) -> None:
        """Wake the projector and update state only after success."""
        if self.runtime.debug_logging:
            _LOGGER.info(
                "Debug: XGIMI wake requested backend=%s",
                self.runtime.effective_wake_backend,
            )
        try:
            await self.runtime.async_wake()
        except asyncio.CancelledError:
            raise
        except WakeBackendError as err:
            raise HomeAssistantError(str(err)) from err
        except Exception as err:
            safe_error = WakeBackendError()
            raise HomeAssistantError(str(safe_error)) from err

        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the XGIMI projector on."""
        await self._async_wake()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the XGIMI projector off."""
        await self.runtime.api.async_send_command(COMMAND_POWER_OFF)

    async def async_send_command(
        self,
        command: Iterable[str],
        **kwargs: Any,
    ) -> None:
        """Send one or more remote commands."""
        for single_command in command:
            if self.runtime.debug_logging:
                _LOGGER.info("Debug: XGIMI remote command=%s", single_command)
            if single_command == COMMAND_POWER_ON:
                await self._async_wake()
            else:
                await self.runtime.api.async_send_command(single_command)
