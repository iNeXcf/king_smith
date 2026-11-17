"""Cover manual configuration, discovery, and duplicate prevention."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import AbortFlow, FlowResultType

from custom_components.king_smith.config_flow import WalkingpadConfigFlow


@pytest.fixture
def flow(hass):
    """Create a flow backed by a real Home Assistant config manager."""
    result = WalkingpadConfigFlow()
    result.hass = hass
    result.context = {"source": "user"}
    result.flow_id = "test-flow"
    result.handler = "king_smith"
    return result


async def test_manual_entry_point(flow):
    """Open a usable configuration form without Bluetooth discovery first."""
    with patch(
        "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
        return_value=[],
    ):
        result = await flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "device"
    result["data_schema"]({"name": "My Z1", "mac": "AA:BB:CC:DD:EE:FF"})


async def test_create_discovered_z1(flow):
    """Store the advertised name separately from the user's friendly name."""
    info = SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF", name="KS-HD-Z1D", connectable=True
    )
    with patch(
        "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
        return_value=[info],
    ), patch(
        "custom_components.king_smith.config_flow.bluetooth.async_last_service_info",
        return_value=info,
    ):
        result = await flow.async_step_bluetooth(info)
        assert result["type"] == FlowResultType.FORM
        result = await flow.async_step_device(
            {"name": "Desk treadmill", "mac": info.address}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "name": "Desk treadmill",
        "mac": info.address,
        "ble_name": "KS-HD-Z1D",
        "device_profile": "z1",
    }
    assert flow.unique_id == "aa:bb:cc:dd:ee:ff"


async def test_create_z1_when_proxy_exposes_local_name_only(flow):
    """Prefer the actual advertised local name over a proxy device name."""
    info = SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF",
        name="AA-BB-CC-DD-EE-FF",
        advertisement=SimpleNamespace(local_name="KS-HD-Z1D"),
        service_uuids=[],
        connectable=True,
    )
    with patch(
        "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
        return_value=[info],
    ), patch(
        "custom_components.king_smith.config_flow.bluetooth.async_last_service_info",
        return_value=info,
    ):
        result = await flow.async_step_device(
            {"name": "Desk treadmill", "mac": info.address}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["ble_name"] == "KS-HD-Z1D"


async def test_create_z1_from_anonymous_ftms_advertisement(flow):
    """Accept a connectable FTMS advert even when a proxy omitted local_name."""
    info = SimpleNamespace(
        address="AA:BB:CC:DD:EE:FF",
        name="AA-BB-CC-DD-EE-FF",
        advertisement=SimpleNamespace(local_name=None),
        service_uuids=["00001826-0000-1000-8000-00805F9B34FB"],
        connectable=True,
    )
    with patch(
        "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
        return_value=[info],
    ), patch(
        "custom_components.king_smith.config_flow.bluetooth.async_last_service_info",
        return_value=info,
    ):
        result = await flow.async_step_device(
            {"name": "Desk treadmill", "mac": info.address}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["ble_name"] == "KS-HD-Z1D"


async def test_duplicate_is_rejected(flow, hass, entry):
    """Recognize an existing entry when the address uses different casing."""
    hass.config_entries._entries[entry.entry_id] = entry
    with pytest.raises(AbortFlow) as error:
        await flow.async_step_device({"name": "Duplicate", "mac": "aa:bb:cc:dd:ee:ff"})
    assert error.value.reason == "already_configured"


async def test_unreachable_device_keeps_form(flow):
    """Explain missing connectable Bluetooth sources during manual setup."""
    with patch(
        "custom_components.king_smith.config_flow.bluetooth.async_last_service_info",
        return_value=None,
    ), patch(
        "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
        return_value=[],
    ):
        result = await flow.async_step_device(
            {"name": "Z1", "mac": "AA:BB:CC:DD:EE:FF"}
        )
    assert result["errors"] == {"base": "device_not_found"}


async def test_invalid_address(flow):
    """Show a field error for malformed Bluetooth addresses."""
    with patch(
        "custom_components.king_smith.config_flow.bluetooth.async_discovered_service_info",
        return_value=[],
    ):
        result = await flow.async_step_device({"name": "Z1", "mac": "garbage"})
    assert result["errors"] == {"mac": "invalid_address"}


async def test_nonconnectable_discovery(flow):
    """Require a scanner capable of opening the treadmill connection."""
    result = await flow.async_step_bluetooth(SimpleNamespace(connectable=False))
    assert result["reason"] == "not_connectable"
