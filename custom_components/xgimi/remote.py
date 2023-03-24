"""Support for the Xgimi Projector."""

from collections.abc import Iterable
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .pyxgimi import XgimiApi
import asyncio


from homeassistant.components.remote import (
    RemoteEntity,
)

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    config = hass.data[DOMAIN][config_entry.entry_id]
    host = config[CONF_HOST]
    name = config[CONF_NAME]
    token = config[CONF_TOKEN]

    unique_id = config_entry.unique_id
    assert unique_id is not None

    xgimi_api = XgimiApi(ip=host, command_port=16735, advance_port=16750, alive_port=554,
                         manufacturer_data=token)
    async_add_entities([XgimiRemote(xgimi_api, name, unique_id)])

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Xiaomi TV platform."""

    # If a hostname is set. Discovery is skipped.
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    unique_id = f"{name}-{token}"

    xgimi_api = XgimiApi(ip=host, command_port=16735, advance_port=16750, alive_port=554,
                         manufacturer_data=token)
    async_add_entities([XgimiRemote(xgimi_api, name, unique_id)])


class XgimiRemote(RemoteEntity):
    """An entity for Xgimi Projector
    """

    def __init__(self, xgimi_api, name, unique_id):
        self.xgimi_api = xgimi_api
        self._name = name
        self._icon = "mdi:projector"
        self._unique_id = unique_id

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

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._unique_id

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