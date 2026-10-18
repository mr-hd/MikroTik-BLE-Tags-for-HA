"""Manual setup, recovery, duplicates, and discovery."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mikrotik_ble_tags.const import DOMAIN

from .conftest import ADDRESS, PAYLOAD, make_service_info


async def start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def finish(hass, flow_id, values):
    with patch(
        "custom_components.mikrotik_ble_tags.async_setup_entry",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(flow_id, values)
        await hass.async_block_till_done()
        return result


async def test_manual_setup(hass, bluetooth_backend):
    result = await start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await finish(
        hass, result["flow_id"], {"address": ADDRESS.lower(), "name": "  Garden  "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"address": ADDRESS, "name": "Garden"}
    assert result["result"].unique_id == ADDRESS
    bluetooth_backend.last_info.assert_called_with(hass, ADDRESS, connectable=False)


async def test_bad_address_recovers(hass, bluetooth_backend):
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "invalid", "name": "Tag"}
    )
    assert result["errors"] == {"address": "invalid_address"}
    result = await finish(hass, result["flow_id"], {"address": ADDRESS, "name": "   "})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["name"] == "MikroTik Tag"


async def test_duplicate(hass, bluetooth_backend):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.add_to_hass(hass)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": ADDRESS.lower(), "name": "Duplicate"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    "condition,error",
    [
        ("no_scanner", "no_scanner"),
        ("timeout", "not_found"),
        ("version", "unsupported_packet"),
        ("encrypted", "encrypted"),
    ],
)
async def test_setup_errors_recover(hass, bluetooth_backend, condition, error):
    if condition in ("no_scanner", "timeout"):
        bluetooth_backend.last_info.return_value = None
    if condition == "no_scanner":
        bluetooth_backend.scanners.return_value = 0
    elif condition == "timeout":
        bluetooth_backend.process.side_effect = TimeoutError
    elif condition == "version":
        bluetooth_backend.last_info.return_value = make_service_info(
            b"\x02" + PAYLOAD[1:]
        )
    else:
        bluetooth_backend.last_info.return_value = make_service_info(
            PAYLOAD[:1] + b"\x01" + PAYLOAD[2:]
        )

    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": ADDRESS, "name": "Tag"}
    )
    assert result["errors"] == {"base": error}
    bluetooth_backend.last_info.return_value = make_service_info()
    bluetooth_backend.scanners.return_value = 1
    result = await finish(hass, result["flow_id"], {"address": ADDRESS, "name": "Tag"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == ADDRESS


async def test_wait_for_advertisement(hass, bluetooth_backend):
    bluetooth_backend.last_info.return_value = None
    bluetooth_backend.process.return_value = make_service_info()
    result = await start(hass)
    result = await finish(hass, result["flow_id"], {"address": ADDRESS, "name": "Tag"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    args = bluetooth_backend.process.call_args.args
    assert args[1](make_service_info())
    assert not args[1](make_service_info(address="11:22:33:44:55:66"))


async def test_discovery(hass, bluetooth_backend):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=make_service_info(),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"
    result = await finish(hass, result["flow_id"], {"name": "Discovered"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == ADDRESS


@pytest.mark.parametrize(
    "payload,error",
    [
        (b"\x02" + PAYLOAD[1:], "unsupported_packet"),
        (PAYLOAD[:1] + b"\x01" + PAYLOAD[2:], "encrypted"),
    ],
)
async def test_reject_unsupported_discovery(hass, bluetooth_backend, payload, error):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=make_service_info(payload),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == error


async def test_duplicate_discovery(hass, bluetooth_backend):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, data={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=make_service_info(),
    )
    assert result["reason"] == "already_configured"
