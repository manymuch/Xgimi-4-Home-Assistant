"""Support for the Xgimi Projector."""

from collections.abc import Iterable
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN
from .pyxgimi import XgimiApi
import asyncio


from homeassistant.components.remote import (
    RemoteEntity,
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Xiaomi TV platform."""

    # If a hostname is set. Discovery is skipped.
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)

    xgimi_api = XgimiApi(ip=host, command_port=16735, advance_port=16750, alive_port=554,
                         manufacturer_data=token)
    async_add_entities([XgimiRemote(xgimi_api, name)])


class XgimiRemote(RemoteEntity):
    """An entity for Xgimi Projector
    """

    def __init__(self, xgimi_api, name):
        self.xgimi_api = xgimi_api
        self._name = name
        self._icon = "mdi:projector"

    async def async_update(self):
        """Retrieve latest state."""
        await self.xgimi_api.async_fetch_data()

    @property
    def is_on(self):
        """Return true if remote is on."""
        return self.xgimi_api._is_on

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use for device if any."""
        return self._icon

    async def async_turn_on(self, **kwargs):
        """Turn the Xgimi Projector On."""
        # Do the turning on.
        await self.xgimi_api.async_send_command("poweron")

    async def async_turn_off(self, **kwargs):
        """Turn the Xgimi Projector Off."""
        # Do the turning off.
        await self.xgimi_api.async_send_command("poweroff")

    async def async_send_command(self, command: Iterable[str], **kwargs) -> None:
        """Send a command to one of the devices."""
        for single_command in command:
            await self.xgimi_api.async_send_command(single_command)