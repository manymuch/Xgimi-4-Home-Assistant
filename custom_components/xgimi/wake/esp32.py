"""ESPHome ESP32 wake backend."""

from __future__ import annotations

from typing import Any

from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from ..const import ESP32_WAKE_ENTITY_DOMAIN, WAKE_BACKEND_ESP32
from .exceptions import (
    ESP32WakeEntityDomainError,
    ESP32WakeEntityMissingError,
    ESP32WakeEntityUnavailableError,
    ESP32WakeServiceError,
    WakeBackendClosedError,
    WakeBackendError,
)

BUTTON_PRESS_SERVICE = "press"


class ESP32WakeBackend:
    """Wake a projector by pressing a dedicated ESPHome button."""

    backend_type = WAKE_BACKEND_ESP32

    def __init__(self, hass: HomeAssistant, entity_id: str | None) -> None:
        """Initialize the ESP32 wake backend."""
        self._hass = hass
        self.entity_id = entity_id
        self._closed = False

    def _get_state(self) -> Any:
        """Validate the configured entity and return its state."""
        if not self.entity_id:
            raise ESP32WakeEntityMissingError

        domain, separator, _ = self.entity_id.partition(".")
        if not separator or domain != ESP32_WAKE_ENTITY_DOMAIN:
            raise ESP32WakeEntityDomainError

        state = self._hass.states.get(self.entity_id)
        if state is None:
            raise ESP32WakeEntityMissingError
        # Button entities commonly remain STATE_UNKNOWN until their first
        # press. Only STATE_UNAVAILABLE means the entity cannot be called.
        if state.state == STATE_UNAVAILABLE:
            raise ESP32WakeEntityUnavailableError
        return state

    async def async_probe(self) -> None:
        """Verify that the ESPHome wake button is available."""
        if self._closed:
            raise WakeBackendClosedError
        self._get_state()

    async def async_wake(self) -> None:
        """Press the ESPHome wake button."""
        await self.async_probe()
        assert self.entity_id is not None
        try:
            await self._hass.services.async_call(
                ESP32_WAKE_ENTITY_DOMAIN,
                BUTTON_PRESS_SERVICE,
                {ATTR_ENTITY_ID: self.entity_id},
                blocking=True,
            )
        except WakeBackendError:
            raise
        except Exception as err:
            raise ESP32WakeServiceError from err

    async def async_close(self) -> None:
        """Close the backend."""
        self._closed = True

    def diagnostics(self) -> dict[str, Any]:
        """Return safe ESP32 backend diagnostics."""
        state = self._hass.states.get(self.entity_id) if self.entity_id else None
        available = bool(state is not None and state.state != STATE_UNAVAILABLE)
        return {
            "esp32_wake_entity": self.entity_id,
            "esp32_entity_available": available,
        }
