"""Protocol edge cases and the vendor's published example."""

import pytest

from custom_components.mikrotik_ble_tags.decoder import decode_mikrotik_v1

from .conftest import PAYLOAD


@pytest.mark.parametrize(
    "prefix", [b"", bytes.fromhex("15ff4f09"), bytes.fromhex("02010615ff4f09")]
)
def test_vendor_example(prefix):
    result = decode_mikrotik_v1(prefix + PAYLOAD)
    assert result is not None
    assert result.version == 1
    assert not result.encrypted
    assert result.salt == 42702
    assert result.seq == result.salt
    assert result.temperature_c == 28.625
    assert result.uptime_s == 5703825
    assert result.battery_pct == 95
    assert result.acc_z_g == 2 / 256


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x01",
        PAYLOAD[:-1],
        PAYLOAD + b"\x00",
        b"\x02" + PAYLOAD[1:],
        bytes.fromhex("15ff4f09") + PAYLOAD[:-1],
    ],
)
def test_reject_invalid_packets(payload):
    assert decode_mikrotik_v1(payload) is None


def test_userdata_is_a_bitmask():
    payload = bytearray(PAYLOAD)
    payload[1] = 0x02
    assert not decode_mikrotik_v1(bytes(payload)).encrypted
    assert decode_mikrotik_v1(bytes(payload)).temperature_c == 28.625


@pytest.mark.parametrize("flags", [0x01, 0x03, 0xFF])
def test_ciphertext_is_not_decoded(flags):
    payload = bytearray(PAYLOAD)
    payload[1] = flags
    result = decode_mikrotik_v1(bytes(payload))
    assert result.encrypted
    assert result.temperature_c is None
    assert result.battery_pct is None
    assert result.salt is None


def test_accelerometer_disabled():
    payload = bytearray(PAYLOAD)
    payload[16] = 0x40
    result = decode_mikrotik_v1(bytes(payload))
    assert result.acc_x_g is None
    assert result.acc_y_g is None
    assert result.acc_z_g is None
    assert result.temperature_c == 28.625


@pytest.mark.parametrize(
    "battery,expected", [(0, 0), (100, 100), (101, None), (255, None)]
)
def test_battery_bounds(battery, expected):
    payload = bytearray(PAYLOAD)
    payload[17] = battery
    assert decode_mikrotik_v1(bytes(payload)).battery_pct == expected


def test_signed_values():
    payload = bytearray(PAYLOAD)
    payload[4:6] = (-256).to_bytes(2, "little", signed=True)
    payload[10:12] = (-2560).to_bytes(2, "little", signed=True)
    result = decode_mikrotik_v1(bytes(payload))
    assert result.acc_x_g == -1.0
    assert result.temperature_c == -10.0


def test_zero_padding_and_unrelated_ad():
    assert decode_mikrotik_v1(b"\x00") is None
    assert decode_mikrotik_v1(bytes.fromhex("020106")) is None
