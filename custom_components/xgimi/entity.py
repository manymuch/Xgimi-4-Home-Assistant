"""Shared entity helpers for XGIMI devices."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DEVICE_MODEL, DOMAIN, MANUFACTURER


def xgimi_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the stable Home Assistant device information for an entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=DEVICE_MODEL,
    )
