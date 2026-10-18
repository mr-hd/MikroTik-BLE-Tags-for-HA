"""Real Home Assistant fixtures with only the Bluetooth radio mocked."""

import inspect
from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

ADDRESS = "AA:BB:CC:DD:EE:FF"
PAYLOAD = bytes.fromhex("0100cea6000000000200a01c91085700005f")


def make_service_info(
    payload: bytes | None = PAYLOAD, address: str = ADDRESS
) -> BluetoothServiceInfoBleak:
    """Build an advertisement heard by a receive-only remote adapter."""
    device_kwargs = (
        {"rssi": -61} if "rssi" in inspect.signature(BLEDevice).parameters else {}
    )
    return BluetoothServiceInfoBleak(
        name="MikroTik Tag",
        address=address,
        rssi=-61,
        manufacturer_data={2383: payload} if payload is not None else {},
        service_data={},
        service_uuids=[],
        source="test-proxy",
        device=BLEDevice(address, "MikroTik Tag", {}, **device_kwargs),
        advertisement=None,
        connectable=False,
        time=1234.0,
        tx_power=None,
    )


@pytest.fixture(autouse=True)
def custom_integration_enabled(enable_custom_integrations):
    """Load the actual integration from this repository."""


@pytest.fixture
def bluetooth_backend(hass) -> Generator[SimpleNamespace]:
    """Skip physical radio setup and capture real coordinator subscriptions."""
    hass.config.components.add("bluetooth")
    radio = SimpleNamespace(
        update_callback=None,
        unavailable_callback=None,
        unsubscribe_updates=Mock(),
        unsubscribe_unavailable=Mock(),
    )

    def register(hass_arg, callback, matcher, mode, **kwargs):
        radio.update_callback = callback
        radio.matcher = matcher
        radio.mode = mode
        return radio.unsubscribe_updates

    def track(hass_arg, callback, address, connectable):
        radio.unavailable_callback = callback
        radio.connectable = connectable
        return radio.unsubscribe_unavailable

    prefix = "homeassistant.components.bluetooth.update_coordinator."
    with (
        patch(prefix + "async_address_present", return_value=False),
        patch(prefix + "async_last_service_info", return_value=None),
        patch(prefix + "async_register_callback", side_effect=register),
        patch(prefix + "async_track_unavailable", side_effect=track),
        patch(
            "homeassistant.components.bluetooth.async_last_service_info",
            return_value=make_service_info(),
        ) as last_info,
        patch(
            "homeassistant.components.bluetooth.async_scanner_count", return_value=1
        ) as scanners,
        patch(
            "homeassistant.components.bluetooth.async_process_advertisements",
            new_callable=AsyncMock,
        ) as process,
        patch(
            "homeassistant.components.bluetooth.async_rediscover_address"
        ) as rediscover,
    ):
        radio.last_info = last_info
        radio.scanners = scanners
        radio.process = process
        radio.rediscover = rediscover
        yield radio
