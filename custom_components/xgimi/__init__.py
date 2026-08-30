"""XGIMI projector integration."""

from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, STATE_UNAVAILABLE, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, CONF_ALIVE_PORT, DEFAULT_ALIVE_PORT, WAKE_BACKEND_AUTO
from .pyxgimi import XgimiApi
from .repairs import (
    async_clear_esp32_repairs,
    async_clear_wake_repairs,
    async_set_wake_repair,
)
from .runtime import XgimiRuntimeData
from .wake.exceptions import NoWakeBackendAvailableError, WakeBackendError
from .wake.factory import (
    create_wake_backend,
    wake_backend_config,
)

PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.REMOTE,
    Platform.SELECT,
    Platform.SENSOR,
]

XgimiConfigEntry = ConfigEntry[XgimiRuntimeData]


def _async_register_esp32_repair_recovery(
    hass: HomeAssistant,
    entry: XgimiConfigEntry,
) -> None:
    """Clear a stale ESP32 repair once the wake button becomes available.

    ESPHome devices can take longer than the startup probe window to
    reconnect after an HA restart. When the configured button finally
    becomes available, remove the stale repair instead of leaving it on
    screen until the next reload.
    """
    config = wake_backend_config(entry)
    if config.esp32_entity_id is None:
        return

    @callback
    def _async_on_button_change(event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state == STATE_UNAVAILABLE:
            return
        async_clear_esp32_repairs(hass, entry.entry_id)
        unsub()

    unsub = async_track_state_change_event(
        hass,
        config.esp32_entity_id,
        _async_on_button_change,
    )
    entry.async_on_unload(unsub)


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
    effective_backend: str | None = config.candidate_backend
    setup_error: WakeBackendError | None = None

    try:
        await wake_backend.async_probe()
    except WakeBackendError as err:
        setup_error = err
        if (
            config.configured_backend == WAKE_BACKEND_AUTO
            and not config.esp32_entity_id
        ):
            setup_error = NoWakeBackendAvailableError(err)
            effective_backend = None

    runtime = XgimiRuntimeData(
        hass=hass,
        entry_id=entry.entry_id,
        api=api,
        wake_backend=wake_backend,
        configured_wake_backend=config.configured_backend,
        effective_wake_backend=effective_backend,
        advertisement_duration=config.advertisement_duration,
        esp32_wake_entity=config.esp32_entity_id,
        debug_logging=config.debug_logging,
        setup_wake_error=setup_error,
        config_entry=entry,
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

    _async_register_esp32_repair_recovery(hass, entry)
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
