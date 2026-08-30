"""XGIMI projector integration."""

from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ALIVE_PORT,
    DEFAULT_ALIVE_PORT,
    DOMAIN,
    WAKE_BACKEND_LOCAL,
)
from .pyxgimi import XgimiApi
from .repairs import async_clear_wake_repairs, async_set_wake_repair
from .runtime import XgimiRuntimeData
from .wake.exceptions import WakeBackendError
from .wake.factory import create_wake_backend, wake_backend_config

PLATFORMS: Final[list[Platform]] = [Platform.REMOTE]

XgimiConfigEntry = ConfigEntry[XgimiRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: XgimiConfigEntry,
) -> bool:
    """Set up an XGIMI config entry."""
    config = wake_backend_config(entry)
    api = XgimiApi(
        ip=entry.data[CONF_HOST],
        alive_port=int(entry.options.get(CONF_ALIVE_PORT, DEFAULT_ALIVE_PORT)),
    )
    wake_backend = create_wake_backend(hass, entry)
    setup_error: WakeBackendError | None = None

    if config.configured_backend == WAKE_BACKEND_LOCAL:
        try:
            await wake_backend.async_probe()
        except WakeBackendError as err:
            setup_error = err

    runtime = XgimiRuntimeData(
        hass=hass,
        entry_id=entry.entry_id,
        api=api,
        wake_backend=wake_backend,
        configured_wake_backend=config.configured_backend,
        wake_button=config.wake_button,
        advertisement_duration=config.advertisement_duration,
        scan_interval=config.scan_interval,
        debug_logging=config.debug_logging,
        setup_wake_error=setup_error,
    )
    entry.runtime_data = runtime
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    if setup_error is None:
        async_clear_wake_repairs(hass, entry.entry_id)
    else:
        async_set_wake_repair(hass, entry.entry_id, setup_error)

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await runtime.async_close()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: XgimiConfigEntry,
) -> bool:
    """Unload an XGIMI config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    await entry.runtime_data.async_close()
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
