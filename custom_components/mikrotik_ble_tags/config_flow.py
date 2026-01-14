from __future__ import annotations

import re
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DOMAIN

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


class MikrotikBleTagsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            typed = (user_input.get(CONF_ADDRESS) or "").strip()
            name = (user_input.get(CONF_NAME) or "MikroTik Tag").strip()

            address = typed.upper()

            if not MAC_RE.match(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()

                title = f"{name} ({address})"

                return self.async_create_entry(
                    title=title,
                    data={CONF_ADDRESS: address, CONF_NAME: name},
                )

        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS, default=defaults.get(CONF_ADDRESS, "")): str,
                vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "MikroTik Tag")): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
