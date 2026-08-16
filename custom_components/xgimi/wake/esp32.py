"""ESPHome ESP32 wake backend."""

from __future__ import annotations

import logging
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
_LOGGER = logging.getLogger(__name__)


class ESP32WakeBackend:
    """Wake a projector by pressing a dedicated ESPHome button."""

    backend_type = WAKE_BACKEND_ESP32

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str | None,
        *,
        debug_logging: bool = False,
    ) -> None:
        """Initialize the ESP32 wake backend."""
        self._hass = hass
        self.entity_id = entity_id
        self._debug_logging = debug_logging
        self._closed = False

    def _log_debug(self, message: str, *args: Any) -> None:
        """Emit optional ESPHome wake diagnostics."""
        if self._debug_logging:
            _LOGGER.info("Debug: " + message, *args)

    def _get_state(self) -> Any:
        """Validate the configured entity and return its state."""
        if not self.entity_id:
            self._log_debug("ESP32 wake probe failed: no entity is configured")
            raise ESP32WakeEntityMissingError

        domain, separator, _ = self.entity_id.partition(".")
        if not separator or domain != ESP32_WAKE_ENTITY_DOMAIN:
            self._log_debug(
                "ESP32 wake probe failed: entity has unsupported domain entity=%s",
                self.entity_id,
            )
            raise ESP32WakeEntityDomainError

        state = self._hass.states.get(self.entity_id)
        if state is None:
            self._log_debug(
                "ESP32 wake probe failed: entity does not exist entity=%s",
                self.entity_id,
            )
            raise ESP32WakeEntityMissingError
        # Button entities commonly remain STATE_UNKNOWN until their first
        # press. Only STATE_UNAVAILABLE means the entity cannot be called.
        if state.state == STATE_UNAVAILABLE:
            self._log_debug(
                "ESP32 wake probe failed: entity is unavailable entity=%s",
                self.entity_id,
            )
            raise ESP32WakeEntityUnavailableError
        self._log_debug(
            "ESP32 wake entity validated entity=%s state=%s",
            self.entity_id,
            state.state,
        )
        return state

    async def async_probe(self) -> None:
        """Verify that the ESPHome wake button is available."""
        if self._closed:
            raise WakeBackendClosedError
        self._get_state()
        self._log_debug("ESP32 wake probe completed successfully")

    async def async_wake(self) -> None:
        """Press the ESPHome wake button."""
        await self.async_probe()
        assert self.entity_id is not None
        self._log_debug(
            "Calling Home Assistant button.press for ESP32 wake entity=%s",
            self.entity_id,
        )
        try:
            await self._hass.services.async_call(
                ESP32_WAKE_ENTITY_DOMAIN,
                BUTTON_PRESS_SERVICE,
                {ATTR_ENTITY_ID: self.entity_id},
                blocking=True,
            )
            self._log_debug("ESP32 wake button service call completed")
        except WakeBackendError as err:
            self._log_debug(
                "ESP32 wake button service call failed error_type=%s",
                type(err).__name__,
            )
            raise
        except Exception as err:
            self._log_debug(
                "ESP32 wake button service call failed error_type=%s",
                type(err).__name__,
            )
            raise ESP32WakeServiceError from err

    async def async_close(self) -> None:
        """Close the backend."""
        self._closed = True

    def diagnostics(self) -> dict[str, Any]:
        """Return safe ESP32 backend diagnostics."""
        state = self._hass.states.get(self.entity_id) if self.entity_id else None
        available = bool(state is not None and state.state != STATE_UNAVAILABLE)
        return {
            "debug_logging": self._debug_logging,
            "esp32_wake_entity": self.entity_id,
            "esp32_entity_available": available,
        }
