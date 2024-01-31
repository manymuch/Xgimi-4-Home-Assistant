from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.util.network import is_host_valid

from .const import (
    DOMAIN,
)


class XgimiConfigFLow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            name = user_input[CONF_NAME]
            token = user_input[CONF_TOKEN]
            if not is_host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(f"{name}-{token}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, vol.UNDEFINED)): str,
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, vol.UNDEFINED)): str,
                vol.Required(CONF_TOKEN, default=user_input.get(CONF_TOKEN, vol.UNDEFINED)): str,
            }),
            errors=errors,
        )
