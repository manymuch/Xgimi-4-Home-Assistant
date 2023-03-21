"""Xgimi Projector Integration"""
from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS: Final[list[Platform]] = [
    Platform.REMOTE,
]

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = {}
    for k in [CONF_HOST, CONF_TOKEN, CONF_NAME]:
        config[k] = config_entry.data.get(k)

    hass.data[DOMAIN][config_entry.entry_id] = config

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok