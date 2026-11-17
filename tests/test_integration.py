"""Run setup, real entity platforms, service calls, and unload in HA."""

import json
import importlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from homeassistant import loader
from homeassistant.config_entries import ConfigEntryState
from walkingpad_controller.const import ProtocolType
from walkingpad_controller.models import TreadmillStatus


@pytest.fixture
def controller():
    """Simulate a treadmill while using the real integration and platforms."""
    result = MagicMock()
    result.connected = False
    result.protocol = ProtocolType.FTMS
    result.min_speed = 1.6
    result.max_speed = 6.4
    result.speed_increment = 0.1
    result.firmware_version = "V0.0.6"

    def report(speed=0):
        result.register_status_callback.call_args.args[0](
            TreadmillStatus(speed=speed, duration=100, steps=200, distance=300)
        )

    async def connect():
        result.connected = True
        report()

    async def disconnect():
        result.connected = False
        result.register_disconnect_callback.call_args.args[0]()

    async def set_speed(speed):
        report(speed)
        return True

    result.connect = AsyncMock(side_effect=connect)
    result.disconnect = AsyncMock(side_effect=disconnect)
    result.set_speed = AsyncMock(side_effect=set_speed)
    result.start = AsyncMock(return_value=True)
    result.stop = AsyncMock(return_value=True)
    result.sleep = AsyncMock(return_value=True)
    return result


async def prepare(hass, entry):
    """Load HA infrastructure and register the integration under test."""
    hass.config.skip_pip = True
    hass.config.components.add("bluetooth_adapters")
    path = Path(__file__).resolve().parents[1] / "custom_components" / "king_smith"
    manifest = json.loads((path / "manifest.json").read_text())
    # Bluetooth transport is supplied by the simulated controller in these tests.
    manifest["dependencies"] = []
    integration = loader.Integration(
        hass,
        "custom_components.king_smith",
        path,
        manifest,
        top_level_files={file.name for file in path.iterdir()},
    )
    hass.data[loader.DATA_INTEGRATIONS]["king_smith"] = integration
    hass.data[loader.DATA_CUSTOM_COMPONENTS] = {"king_smith": integration}
    hass.data[loader.DATA_COMPONENTS]["king_smith"] = importlib.import_module(
        "custom_components.king_smith"
    )
    hass.config.components.add("king_smith")
    hass.config_entries._entries[entry.entry_id] = entry


async def test_entities_and_speed_service(hass, entry, controller):
    """Create all entities and control speed through the real HA service."""
    await prepare(hass, entry)
    device = BLEDevice("AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", {})
    with patch(
        "custom_components.king_smith.walking_pad.KingsmithController",
        return_value=controller,
    ), patch(
        "custom_components.king_smith.bluetooth.async_ble_device_from_address",
        return_value=device,
    ), patch("custom_components.king_smith.bluetooth.async_rediscover_address"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        states = hass.states.async_all()
        assert len(states) == 14
        assert len([state for state in states if state.domain == "sensor"]) == 8
        assert len([state for state in states if state.domain == "button"]) == 3
        assert len([state for state in states if state.domain == "number"]) == 2
        sleep = next(
            state
            for state in states
            if state.domain == "button"
            and state.attributes["friendly_name"].endswith("Sleep")
        )
        speed = next(
            state
            for state in states
            if state.domain == "number" and state.attributes["max"] == 6.0
        )
        adjustment = next(
            state
            for state in states
            if state.domain == "number" and state.attributes["max"] == 1.0
        )
        assert speed.attributes["min"] == 1.0
        assert speed.attributes["max"] == 6.0
        assert speed.attributes["step"] == 0.1
        assert speed.attributes["mode"] == "slider"
        assert float(speed.state) == 1.0
        assert float(adjustment.state) == 0.5
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": sleep.entity_id},
            blocking=True,
        )
        controller.sleep.assert_awaited_once()
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": speed.entity_id, "value": 3.3},
            blocking=True,
        )
        controller.set_speed.assert_awaited_once_with(3.3)
        assert hass.states.get(speed.entity_id).state == "3.3"
        coordinator = entry.runtime_data
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        controller.disconnect.assert_awaited_once()
        assert coordinator.api._callbacks == []
        assert coordinator.api._disconnect_callbacks == []


async def test_failed_connection_retries_setup(hass, entry, controller):
    """Fail setup cleanly and release the client if Bluetooth is unavailable."""
    await prepare(hass, entry)
    device = BLEDevice("AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", {})
    controller.connect.side_effect = BleakError("proxy unavailable")
    with patch(
        "custom_components.king_smith.walking_pad.KingsmithController",
        return_value=controller,
    ), patch(
        "custom_components.king_smith.bluetooth.async_ble_device_from_address",
        return_value=device,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state == ConfigEntryState.SETUP_RETRY
    assert not hass.states.async_all()
    assert not controller.connected


@pytest.mark.parametrize("version,expected", [(0.1, True), (1, True), (2, False)])
async def test_config_entry_migration(hass, entry, version, expected):
    """Preserve saved device data while migrating the old float version."""
    from custom_components.king_smith import async_migrate_entry

    hass.config_entries._entries[entry.entry_id] = entry
    hass.config_entries.async_update_entry(entry, version=version)
    saved = dict(entry.data)
    assert await async_migrate_entry(hass, entry) is expected
    assert entry.data == saved
    assert entry.version == (1 if expected else version)
