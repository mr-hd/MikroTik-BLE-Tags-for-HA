"""Sensors for MikroTik Bluetooth tags."""

from __future__ import annotations

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import MikrotikTagCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the existing set of entities with their original unique IDs."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            MikrotikRssiSensor(coordinator),
            MikrotikRawManufacturerSensor(coordinator),
            MikrotikTempSensor(coordinator),
            MikrotikBatterySensor(coordinator),
            MikrotikUptimeSensor(coordinator),
            MikrotikAccSensor(coordinator, "X"),
            MikrotikAccSensor(coordinator, "Y"),
            MikrotikAccSensor(coordinator, "Z"),
        ]
    )


class MikrotikBaseSensor(
    PassiveBluetoothCoordinatorEntity[MikrotikTagCoordinator], SensorEntity
):
    """Subscribe only while the entity is added to Home Assistant."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, coordinator: MikrotikTagCoordinator, suffix: str, translation_key: str
    ) -> None:
        """Keep the previous MAC_suffix IDs for registry/history continuity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{suffix}"
        self._attr_translation_key = translation_key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=coordinator.device_name,
            manufacturer="MikroTik",
            model="TG-BT5",
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Retain the previously exposed MAC attribute."""
        return {"mac_address": self.coordinator.address}


class MikrotikTelemetrySensor(MikrotikBaseSensor):
    """Never expose stale or invalid telemetry as a live measurement."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Require a supported unencrypted packet and a valid sensor value."""
        return (
            super().available
            and self.coordinator.telemetry_status == "ok"
            and self.native_value is not None
        )


class MikrotikRssiSensor(MikrotikBaseSensor):
    """Bluetooth signal strength."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "dBm"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: MikrotikTagCoordinator) -> None:
        super().__init__(coordinator, "rssi", "rssi")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.rssi


class MikrotikRawManufacturerSensor(MikrotikBaseSensor):
    """Optional verbose packet diagnostics, disabled for new installations."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: MikrotikTagCoordinator) -> None:
        super().__init__(coordinator, "raw", "raw")

    @property
    def native_value(self) -> str:
        if not self.coordinator.manufacturer_dump:
            return "no_mfg_data"
        return "data block (see attributes)"

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes
        attrs["telemetry_status"] = self.coordinator.telemetry_status
        if self.coordinator.manufacturer_dump:
            attrs["manufacturer_data"] = self.coordinator.manufacturer_dump
        if self.coordinator.payload_hex:
            attrs["mikrotik_payload_hex"] = self.coordinator.payload_hex
        if decoded := self.coordinator.decoded:
            attrs["encrypted"] = decoded.encrypted
            if decoded.salt is not None:
                attrs["salt"] = decoded.salt
            if decoded.flags is not None:
                attrs["flags"] = decoded.flags
        return attrs


class MikrotikTempSensor(MikrotikTelemetrySensor):
    """Reported temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: MikrotikTagCoordinator) -> None:
        super().__init__(coordinator, "temp", "temperature")

    @property
    def native_value(self) -> float | None:
        decoded = self.coordinator.decoded
        return decoded.temperature_c if decoded else None


class MikrotikBatterySensor(MikrotikTelemetrySensor):
    """Remaining battery charge."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = "%"
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: MikrotikTagCoordinator) -> None:
        super().__init__(coordinator, "battery", "battery")

    @property
    def native_value(self) -> int | None:
        decoded = self.coordinator.decoded
        return decoded.battery_pct if decoded else None


class MikrotikUptimeSensor(MikrotikTelemetrySensor):
    """Reported seconds since the tag started."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: MikrotikTagCoordinator) -> None:
        super().__init__(coordinator, "uptime", "uptime")

    @property
    def native_value(self) -> int | None:
        decoded = self.coordinator.decoded
        return decoded.uptime_s if decoded else None

    @property
    def extra_state_attributes(self) -> dict:
        attrs = super().extra_state_attributes
        if (seconds := self.native_value) is not None:
            days, remainder = divmod(seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            attrs["uptime_human"] = f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
        return attrs


class MikrotikAccSensor(MikrotikTelemetrySensor):
    """Reported acceleration, with the original unit and unique ID."""

    _attr_native_unit_of_measurement = "G"
    _attr_suggested_display_precision = 3

    def __init__(self, coordinator: MikrotikTagCoordinator, axis: str) -> None:
        if axis not in ("X", "Y", "Z"):
            raise ValueError(f"Unsupported acceleration axis: {axis}")
        self._axis = axis.lower()
        super().__init__(coordinator, f"acc_{self._axis}", f"acc_{self._axis}")

    @property
    def native_value(self) -> float | None:
        if decoded := self.coordinator.decoded:
            return getattr(decoded, f"acc_{self._axis}_g")
        return None
