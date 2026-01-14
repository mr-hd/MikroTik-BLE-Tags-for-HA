from __future__ import annotations

import json
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import CONF_ADDRESS, CONF_NAME, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothScanningMode, BluetoothServiceInfoBleak

from .const import DOMAIN, MIKROTIK_COMPANY_ID
from .decoder import decode_mikrotik_v1

LOGGER = logging.getLogger(__name__)


class TagState:
    def __init__(self, address_norm: str, user_name: str, display_name: str, via_device) -> None:
        self.address_norm = address_norm
        self.user_name = user_name
        self.display_name = display_name
        self.via_device = via_device

        self.rssi: int | None = None
        self.manufacturer_dump: dict[int, str] | None = None
        self.mikrotik_payload_hex: str | None = None

        self.temperature_c: float | None = None
        self.battery_pct: int | None = None
        self.uptime_s: int | None = None
        self.acc_x_g: float | None = None
        self.acc_y_g: float | None = None
        self.acc_z_g: float | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:

    match_address = entry.data[CONF_ADDRESS].strip()
    address_norm = match_address.upper()
    user_name = entry.data.get(CONF_NAME, "MikroTik Tag")

    display_name = entry.title or f"{user_name} ({address_norm})"

    get_dev_id = getattr(bluetooth, "async_get_device_id", None)
    via_device = get_dev_id(hass) if callable(get_dev_id) else None

    tag = TagState(
        address_norm=address_norm,
        user_name=user_name,
        display_name=display_name,
        via_device=via_device,
    )

    entities: list[SensorEntity] = [
        MikrotikRssiSensor(tag),
        MikrotikRawManufacturerSensor(tag),
        MikrotikTempSensor(tag),
        MikrotikBatterySensor(tag),
        MikrotikUptimeSensor(tag),
        MikrotikAccSensor(tag, "X"),
        MikrotikAccSensor(tag, "Y"),
        MikrotikAccSensor(tag, "Z"),
    ]

    async_add_entities(entities, update_before_add=False)

    @callback
    def _ble_callback(service_info: BluetoothServiceInfoBleak, _change: bluetooth.BluetoothChange):
        if service_info.address.upper() != tag.address_norm:
            return

        tag.rssi = service_info.rssi

        if service_info.manufacturer_data:
            tag.manufacturer_dump = {k: v.hex() for k, v in service_info.manufacturer_data.items()}
        else:
            tag.manufacturer_dump = None

        mfg = service_info.manufacturer_data.get(MIKROTIK_COMPANY_ID)
        tag.mikrotik_payload_hex = mfg.hex() if mfg else None

        try:
            if mfg:
                decoded = decode_mikrotik_v1(mfg)
                if decoded and not decoded.encrypted:
                    tag.temperature_c = decoded.temperature_c
                    tag.battery_pct = decoded.battery_pct
                    tag.uptime_s = decoded.uptime_s
                    tag.acc_x_g = decoded.acc_x_g
                    tag.acc_y_g = decoded.acc_y_g
                    tag.acc_z_g = decoded.acc_z_g
        except Exception:
            LOGGER.exception("Decode failed for %s", service_info.address)

        for ent in entities:
            ent.async_write_ha_state()

    unsub = bluetooth.async_register_callback(
        hass,
        _ble_callback,
        {"address": match_address},
        BluetoothScanningMode.ACTIVE,
    )
    entry.async_on_unload(unsub)


class MikrotikBaseSensor(SensorEntity):
    """Common device + attributes for all sensors."""
    _attr_should_poll = False

    def __init__(self, tag: TagState, suffix: str, label: str) -> None:
        self._tag = tag
        self._attr_unique_id = f"{tag.address_norm}_{suffix}"

        self._attr_name = f"{tag.user_name} {label}"

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, self._tag.address_norm)},
            "connections": {("bluetooth", self._tag.address_norm)},
            "name": self._tag.user_name,
            "manufacturer": "MikroTik",
            "model": "TG-BT5",
        }
        if self._tag.via_device:
            info["via_device"] = self._tag.via_device
        return info

    @property
    def extra_state_attributes(self):
        return {"mac_address": self._tag.address_norm}


class MikrotikRssiSensor(MikrotikBaseSensor):
    _attr_native_unit_of_measurement = "dBm"
    _attr_suggested_display_precision = 0

    def __init__(self, tag: TagState) -> None:
        super().__init__(tag, "rssi", "RSSI")

    @property
    def native_value(self):
        return self._tag.rssi


class MikrotikRawManufacturerSensor(MikrotikBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = True

    def __init__(self, tag: TagState) -> None:
        super().__init__(tag, "raw", "Raw")

    @property
    def native_value(self):
        if not self._tag.manufacturer_dump:
            return "no_mfg_data"
        return f"data block (see attributes)"

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes

        if self._tag.manufacturer_dump:
            attrs["manufacturer_data"] = self._tag.manufacturer_dump

        if self._tag.mikrotik_payload_hex:
            attrs["mikrotik_payload_hex"] = self._tag.mikrotik_payload_hex

        return attrs


class MikrotikTempSensor(MikrotikBaseSensor):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, tag: TagState) -> None:
        super().__init__(tag, "temp", "Temperature")

    @property
    def native_value(self):
        return self._tag.temperature_c


class MikrotikBatterySensor(MikrotikBaseSensor):
    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 0

    def __init__(self, tag: TagState) -> None:
        super().__init__(tag, "battery", "Battery")

    @property
    def native_value(self):
        return self._tag.battery_pct


class MikrotikUptimeSensor(MikrotikBaseSensor):
    _attr_native_unit_of_measurement = "s"
    _attr_suggested_display_precision = 0

    def __init__(self, tag: TagState) -> None:
        super().__init__(tag, "uptime", "Uptime")

    @property
    def native_value(self):
        return self._tag.uptime_s

    @property
    def extra_state_attributes(self):
        attrs = dict(super().extra_state_attributes)

        s = self._tag.uptime_s
        if s is None:
            return attrs

        days = s // 86400
        rem = s % 86400
        hours = rem // 3600
        rem %= 3600
        minutes = rem // 60
        seconds = rem % 60

        attrs["uptime_human"] = f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
        return attrs



class MikrotikAccSensor(MikrotikBaseSensor):
    _attr_native_unit_of_measurement = "G"
    _attr_suggested_display_precision = 3

    def __init__(self, tag: TagState, axis: str) -> None:
        self._axis = axis
        super().__init__(tag, f"acc_{axis.lower()}", f"Acc {axis}")

    @property
    def native_value(self):
        if self._axis == "X":
            return self._tag.acc_x_g
        if self._axis == "Y":
            return self._tag.acc_y_g
        return self._tag.acc_z_g
