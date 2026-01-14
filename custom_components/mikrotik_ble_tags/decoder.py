from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


MIKROTIK_COMPANY_ID_LE = b"\x4F\x09"


@dataclass
class MikrotikDecodedV1:
    version: int
    encrypted: bool
    seq: int
    acc_x_g: float
    acc_y_g: float
    acc_z_g: float
    temperature_c: float
    uptime_s: int
    flags: int
    battery_pct: int


def _as_payload(data: bytes) -> bytes:
    if len(data) >= 4 and data[1] == 0xFF and data[2:4] == MIKROTIK_COMPANY_ID_LE:
        return data[4:]
    return data


def decode_mikrotik_v1(data: bytes) -> Optional[MikrotikDecodedV1]:
    payload = _as_payload(data)

    if len(payload) < 18:
        return None

    version = payload[0]
    encrypted = payload[1] != 0

    seq = int.from_bytes(payload[2:4], "little", signed=False)

    # accel values
    acc_x = int.from_bytes(payload[4:6], "little", signed=True) / 256.0
    acc_y = int.from_bytes(payload[6:8], "little", signed=True) / 256.0
    acc_z = int.from_bytes(payload[8:10], "little", signed=True) / 256.0

    # temperature
    temp_c = int.from_bytes(payload[10:12], "little", signed=True) / 256.0

    # uptime
    uptime_s = int.from_bytes(payload[12:16], "little", signed=False)

    flags = payload[16]
    battery = payload[17]

    return MikrotikDecodedV1(
        version=version,
        encrypted=encrypted,
        seq=seq,
        acc_x_g=acc_x,
        acc_y_g=acc_y,
        acc_z_g=acc_z,
        temperature_c=temp_c,
        uptime_s=uptime_s,
        flags=flags,
        battery_pct=battery,
    )
