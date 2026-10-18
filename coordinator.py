"""Share Bluetooth telemetry and availability between registered entities."""

from __future__ import annotations

import logging

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdateCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant, callback

from .const import MIKROTIK_COMPANY_ID
from .decoder import MikrotikDecodedV1, decode_mikrotik_v1

_LOGGER = logging.getLogger(__name__)


class MikrotikTagCoordinator(PassiveBluetoothDataUpdateCoordinator):
    """Receive advertisements from local and receive-only remote adapters."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Create shared state without subscribing before entities exist."""
        self.device_name = entry.data.get(CONF_NAME, "").strip() or "MikroTik Tag"
        self.rssi: int | None = None
        self.manufacturer_dump: dict[int, str] = {}
        self.payload_hex: str | None = None
        self.decoded: MikrotikDecodedV1 | None = None
        self.telemetry_status = "waiting"
        super().__init__(
            hass,
            _LOGGER,
            address=entry.data[CONF_ADDRESS].strip().upper(),
            mode=BluetoothScanningMode.PASSIVE,
            connectable=False,
        )

    @callback
    def _async_handle_bluetooth_event(
        self, service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        """Update one snapshot and notify only subscribed entities."""
        if service_info.address.upper() != self.address:
            return
        self.rssi = service_info.rssi
        self.manufacturer_dump = {
            company: value.hex()
            for company, value in service_info.manufacturer_data.items()
        }
        payload = service_info.manufacturer_data.get(MIKROTIK_COMPANY_ID)
        self.payload_hex = payload.hex() if payload else None
        self.decoded = decode_mikrotik_v1(payload) if payload else None
        if not payload:
            self.telemetry_status = "no_mikrotik_data"
        elif self.decoded is None:
            self.telemetry_status = "unsupported_packet"
        elif self.decoded.encrypted:
            self.telemetry_status = "encrypted"
        else:
            self.telemetry_status = "ok"
        super()._async_handle_bluetooth_event(service_info, change)
