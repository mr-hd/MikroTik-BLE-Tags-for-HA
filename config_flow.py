"""Validated manual setup and Bluetooth discovery for MikroTik BLE Tags."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import ADVERTISEMENT_TIMEOUT, DOMAIN, MIKROTIK_COMPANY_ID
from .decoder import decode_mikrotik_v1

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def _packet_error(info: BluetoothServiceInfoBleak) -> str | None:
    """Check the actual advertisement, rather than just the typed address."""
    payload = info.manufacturer_data.get(MIKROTIK_COMPANY_ID)
    decoded = decode_mikrotik_v1(payload) if payload else None
    if decoded is None:
        return "unsupported_packet"
    if decoded.encrypted:
        return "encrypted"
    return None


class MikrotikBleTagsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up one tag per entry, preserving the previous MAC-based identity."""

    VERSION = 1

    def __init__(self) -> None:
        """Store discovery details until the user confirms the tag."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Validate a manual address against a received advertisement."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = (user_input.get(CONF_ADDRESS) or "").strip().upper()
            name = (user_input.get(CONF_NAME) or "").strip() or "MikroTik Tag"
            if not MAC_RE.fullmatch(address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                info = bluetooth.async_last_service_info(
                    self.hass, address, connectable=False
                )
                if info is None:
                    if not bluetooth.async_scanner_count(self.hass, connectable=False):
                        errors["base"] = "no_scanner"
                    else:
                        try:
                            info = await bluetooth.async_process_advertisements(
                                self.hass,
                                lambda advertisement: (
                                    advertisement.address.upper() == address
                                    and MIKROTIK_COMPANY_ID
                                    in advertisement.manufacturer_data
                                ),
                                {"address": address, "connectable": False},
                                BluetoothScanningMode.PASSIVE,
                                ADVERTISEMENT_TIMEOUT,
                            )
                        except TimeoutError:
                            errors["base"] = "not_found"
                if info is not None:
                    if error := _packet_error(info):
                        errors["base"] = error
                    else:
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=f"{name} ({address})",
                            data={CONF_ADDRESS: address, CONF_NAME: name},
                        )

        defaults = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADDRESS, default=defaults.get(CONF_ADDRESS, "")
                    ): str,
                    vol.Required(
                        CONF_NAME, default=defaults.get(CONF_NAME, "MikroTik Tag")
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Validate a discovered tag before offering it for confirmation."""
        address = discovery_info.address.upper()
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        if error := _packet_error(discovery_info):
            return self.async_abort(reason=error)
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or "MikroTik Tag",
            "address": address,
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Let the user choose a friendly name without typing a MAC address."""
        assert self._discovery_info is not None
        address = self._discovery_info.address.upper()
        advertised_name = self._discovery_info.name
        default_name = (
            advertised_name
            if advertised_name and advertised_name.upper() != address
            else "MikroTik Tag"
        )
        if user_input is not None:
            self._abort_if_unique_id_configured()
            name = (user_input.get(CONF_NAME) or "").strip() or default_name
            return self.async_create_entry(
                title=f"{name} ({address})",
                data={CONF_ADDRESS: address, CONF_NAME: name},
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=default_name): str}
            ),
            description_placeholders={"address": address},
        )
