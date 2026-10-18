"""Exercise actual HA entities, registries, coordinator and unload handling."""

from homeassistant.components.bluetooth import BluetoothChange
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mikrotik_ble_tags.const import DOMAIN

from .conftest import ADDRESS, PAYLOAD, make_service_info


async def setup_tag(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        title=f"Garden ({ADDRESS})",
        data={"address": ADDRESS, "name": "Garden"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def entity_id(hass, suffix):
    return er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{ADDRESS}_{suffix}"
    )


async def test_values_statistics_and_raw_disabled(hass, bluetooth_backend):
    entry = await setup_tag(hass)
    assert entry.runtime_data.connectable is False
    assert bluetooth_backend.matcher["connectable"] is False
    bluetooth_backend.update_callback(
        make_service_info(), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    for suffix in ["temp", "battery", "uptime", "rssi", "acc_x", "acc_y", "acc_z"]:
        state = hass.states.get(entity_id(hass, suffix))
        assert state is not None
        assert state.attributes["state_class"] == "measurement"
    assert hass.states.get(entity_id(hass, "temp")).state == "28.625"
    assert hass.states.get(entity_id(hass, "battery")).state == "95"
    assert (
        hass.states.get(entity_id(hass, "uptime")).attributes["uptime_human"]
        == "66d 00:23:45"
    )
    raw = er.async_get(hass).async_get(entity_id(hass, "raw"))
    assert raw.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(raw.entity_id) is None


async def test_offline_and_recovery(hass, bluetooth_backend):
    await setup_tag(hass)
    info = make_service_info()
    bluetooth_backend.update_callback(info, BluetoothChange.ADVERTISEMENT)
    bluetooth_backend.unavailable_callback(info)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "temp")).state == "unavailable"
    bluetooth_backend.update_callback(info, BluetoothChange.ADVERTISEMENT)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "temp")).state == "28.625"


async def test_bad_telemetry_does_not_reuse_old_values(hass, bluetooth_backend):
    await setup_tag(hass)
    bluetooth_backend.update_callback(
        make_service_info(), BluetoothChange.ADVERTISEMENT
    )
    encrypted = PAYLOAD[:1] + b"\x01" + PAYLOAD[2:]
    bluetooth_backend.update_callback(
        make_service_info(encrypted), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "temp")).state == "unavailable"
    assert hass.states.get(entity_id(hass, "rssi")).state == "-61"
    bluetooth_backend.update_callback(
        make_service_info(None), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "battery")).state == "unavailable"
    bluetooth_backend.update_callback(
        make_service_info(), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "battery")).state == "95"


async def test_disabled_accel_and_invalid_battery(hass, bluetooth_backend):
    await setup_tag(hass)
    payload = bytearray(PAYLOAD)
    payload[16] = 0x40
    payload[17] = 255
    bluetooth_backend.update_callback(
        make_service_info(bytes(payload)), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id(hass, "acc_x")).state == "unavailable"
    assert hass.states.get(entity_id(hass, "battery")).state == "unavailable"
    assert hass.states.get(entity_id(hass, "temp")).state == "28.625"


async def test_existing_entity_ids_are_reused(hass, bluetooth_backend):
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{ADDRESS}_temp",
        suggested_object_id="my_existing_temperature",
    )
    await setup_tag(hass)
    assert entity_id(hass, "temp") == "sensor.my_existing_temperature"
    bluetooth_backend.update_callback(
        make_service_info(), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.my_existing_temperature").state == "28.625"


async def test_unload_cancels_radio_subscriptions(hass, bluetooth_backend):
    entry = await setup_tag(hass)
    coordinator = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    bluetooth_backend.unsubscribe_updates.assert_called_once()
    bluetooth_backend.unsubscribe_unavailable.assert_called_once()
    assert not coordinator._listeners


async def test_disabled_entity_does_not_stop_other_updates(hass, bluetooth_backend):
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{ADDRESS}_rssi",
        suggested_object_id="disabled_rssi",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    await setup_tag(hass)
    bluetooth_backend.update_callback(
        make_service_info(), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.disabled_rssi") is None
    assert hass.states.get(entity_id(hass, "temp")).state == "28.625"
    assert hass.states.get(entity_id(hass, "battery")).state == "95"


async def test_existing_raw_entity_stays_enabled(hass, bluetooth_backend):
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor", DOMAIN, f"{ADDRESS}_raw", suggested_object_id="existing_raw"
    )
    await setup_tag(hass)
    bluetooth_backend.update_callback(
        make_service_info(), BluetoothChange.ADVERTISEMENT
    )
    await hass.async_block_till_done()
    state = hass.states.get("sensor.existing_raw")
    assert state is not None
    assert "state_class" not in state.attributes
    assert state.attributes["telemetry_status"] == "ok"
    assert state.attributes["salt"] == 42702
