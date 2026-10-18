"""Decode MikroTik v1 telemetry without depending on Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MikrotikDecodedV1:
    """Decoded header and, for unencrypted advertisements, telemetry."""

    version: int
    encrypted: bool
    salt: int | None = None
    acc_x_g: float | None = None
    acc_y_g: float | None = None
    acc_z_g: float | None = None
    temperature_c: float | None = None
    uptime_s: int | None = None
    flags: int | None = None
    battery_pct: int | None = None

    @property
    def seq(self) -> int | None:
        """Keep compatibility with the old, incorrectly named salt property."""
        return self.salt


def _as_payload(data: bytes) -> bytes:
    """Accept HA manufacturer bytes or a well-formed BLE AD structure."""
    if len(data) == 18:
        return data
    offset = 0
    while offset < len(data):
        length = data[offset]
        if not length:
            break
        end = offset + length + 1
        if end > len(data):
            return b""
        if length >= 3 and data[offset + 1 : offset + 4] == b"\xff\x4f\x09":
            return data[offset + 4 : end]
        offset = end
    return b""


def decode_mikrotik_v1(data: bytes) -> MikrotikDecodedV1 | None:
    """Decode a supported v1 packet; never interpret ciphertext as telemetry."""
    payload = _as_payload(data)
    if len(payload) != 18 or payload[0] != 1:
        return None
    encrypted = bool(payload[1] & 0x01)
    if encrypted:
        return MikrotikDecodedV1(version=1, encrypted=True)
    flags = payload[16]
    accelerometer_enabled = not flags & 0x40

    def acceleration(offset: int) -> float | None:
        if not accelerometer_enabled:
            return None
        return (
            int.from_bytes(payload[offset : offset + 2], "little", signed=True) / 256.0
        )

    battery = payload[17]
    return MikrotikDecodedV1(
        version=1,
        encrypted=False,
        salt=int.from_bytes(payload[2:4], "little"),
        acc_x_g=acceleration(4),
        acc_y_g=acceleration(6),
        acc_z_g=acceleration(8),
        temperature_c=int.from_bytes(payload[10:12], "little", signed=True) / 256.0,
        uptime_s=int.from_bytes(payload[12:16], "little"),
        flags=flags,
        battery_pct=battery if battery <= 100 else None,
    )
