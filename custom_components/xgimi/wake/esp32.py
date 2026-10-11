"""Home Assistant button wake backend."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from ..const import WAKE_BACKEND_ESP32, WAKE_BUTTON_DOMAINS
from .exceptions import WakeBackendClosedError, WakeButtonServiceError

BUTTON_PRESS_SERVICE = "press"
_LOGGER = logging.getLogger(__name__)


class ESP32WakeBackend:
    """Wake a projector by pressing a configured Home Assistant button."""

    backend_type = WAKE_BACKEND_ESP32

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        *,
        debug_logging: bool = False,
    ) -> None:
        """Initialize the button backend."""
        self._hass = hass
        self.entity_id = entity_id
        self._debug_logging = debug_logging
        self._closed = False

    def _log_debug(self, message: str, *args: Any) -> None:
        """Emit optional wake diagnostics."""
        if self._debug_logging:
            _LOGGER.info("Debug: " + message, *args)

    async def async_probe(self) -> None:
        """Keep setup non-blocking; button availability is HA's responsibility."""
        if self._closed:
            raise WakeBackendClosedError

    async def async_wake(self) -> None:
        """Press the configured button exactly as a Home Assistant automation does."""
        if self._closed:
            raise WakeBackendClosedError
        domain, separator, object_id = self.entity_id.partition(".")
        if not separator or not object_id or domain not in WAKE_BUTTON_DOMAINS:
            raise WakeButtonServiceError
        self._log_debug(
            "Calling %s.%s for wake entity=%s",
            domain,
            BUTTON_PRESS_SERVICE,
            self.entity_id,
        )
        try:
            await self._hass.services.async_call(
                domain,
                BUTTON_PRESS_SERVICE,
                {ATTR_ENTITY_ID: self.entity_id},
                blocking=True,
            )
        except Exception as err:
            self._log_debug(
                "button.press failed error_type=%s",
                type(err).__name__,
            )
            raise WakeButtonServiceError from err
        self._log_debug("button.press completed")

    async def async_close(self) -> None:
        """Close the backend."""
        self._closed = True

    def diagnostics(self) -> dict[str, Any]:
        """Return safe button diagnostics without querying entity state."""
        return {
            "debug_logging": self._debug_logging,
            "wake_button": self.entity_id,
        }
