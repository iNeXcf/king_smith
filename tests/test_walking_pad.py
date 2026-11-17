"""Verify command serialization, errors, and connection recovery."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from homeassistant.exceptions import HomeAssistantError
from walkingpad_controller.const import OperatingMode, ProtocolType
from walkingpad_controller.models import TreadmillStatus

from custom_components.king_smith.walking_pad import WalkingPadApi


@pytest.fixture
def api_and_controller():
    """Connect the API to a controller with realistic units and results."""
    controller = MagicMock()
    controller.connected = True
    controller.protocol = ProtocolType.FTMS
    controller.min_speed = 1.0
    controller.max_speed = 6.0
    controller.speed_increment = 0.1
    for method in ["start", "stop", "set_speed", "switch_mode"]:
        setattr(controller, method, AsyncMock(return_value=True))
    controller.update_state = AsyncMock()
    controller.disconnect = AsyncMock()
    api = WalkingPadApi("Z1", "AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", MagicMock())
    api._ctrl = controller
    return api, controller


async def test_commands_are_serialized(api_and_controller):
    """Keep a stop behind the pending speed command in the same queue."""
    api, controller = api_and_controller
    calls = []

    async def set_speed(value):
        calls.append("speed begin")
        await asyncio.sleep(0.01)
        calls.append("speed end")
        return True

    async def stop():
        calls.append("stop")
        return True

    controller.set_speed.side_effect = set_speed
    controller.stop.side_effect = stop
    await asyncio.gather(api.change_speed(3.3), api.stop_belt())
    assert calls == ["speed begin", "speed end", "stop"]
    controller.set_speed.assert_awaited_once_with(3.3)


async def test_error_releases_queue(api_and_controller):
    """Keep commands and device reports working after an operation fails."""
    api, controller = api_and_controller
    controller.start.side_effect = BleakError("connection problem")
    with pytest.raises(HomeAssistantError):
        await api.start_belt()
    assert not api._lock.locked()
    await api.stop_belt()
    api._on_status_update(TreadmillStatus(speed=2.5))
    assert api.speed == 2.5


async def test_rejected_command_is_reported(api_and_controller):
    """Surface a negative command result instead of claiming success."""
    api, controller = api_and_controller
    controller.start.return_value = False
    with pytest.raises(HomeAssistantError, match="did not confirm"):
        await api.start_belt()
    assert api.moving is None


@pytest.mark.parametrize("speed", [-1, float("nan"), float("inf"), 0.5, 6.1, 2.35])
async def test_invalid_speeds(api_and_controller, speed):
    """Reject invalid speed values before sending motor commands."""
    api, controller = api_and_controller
    with pytest.raises(HomeAssistantError):
        await api.change_speed(speed)
    controller.set_speed.assert_not_awaited()
    controller.start.assert_not_awaited()


async def test_zero_speed_stops(api_and_controller):
    """Send an explicit stop instead of allowing library minimum clamping."""
    api, controller = api_and_controller
    await api.change_speed(0)
    controller.stop.assert_awaited_once()
    controller.set_speed.assert_not_awaited()


def test_mutable_library_status_is_snapshotted(api_and_controller):
    """Calculate cadence against a distinct snapshot of the previous report."""
    api, _ = api_and_controller
    report = TreadmillStatus(speed=3.3, distance=1000, duration=60, steps=100)
    api._on_status_update(report)
    report.duration = 70
    report.steps = 120
    assert api.time == 60
    api._on_status_update(report)
    assert api.step_cadence == 120
    assert api.distance == 1.0
    api._on_status_update(replace(report, duration=1, steps=1))
    assert api.step_cadence == 0


async def test_reconnect_resolves_current_adapter():
    """Build a fresh controller from the current HA Bluetooth source."""
    first = BLEDevice("AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", {"source": "pi"})
    second = BLEDevice("AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", {"source": "proxy"})
    resolve = MagicMock(side_effect=[first, second])
    controllers = []

    def create(device, name):
        controller = MagicMock()
        controller.connected = False

        async def connect():
            controller.connected = True

        async def disconnect():
            controller.connected = False

        controller.connect = AsyncMock(side_effect=connect)
        controller.disconnect = AsyncMock(side_effect=disconnect)
        controllers.append(controller)
        return controller

    api = WalkingPadApi("Z1", first.address, first.name, resolve)
    with patch(
        "custom_components.king_smith.walking_pad.KingsmithController",
        side_effect=create,
    ) as factory:
        await api.connect()
        await api.disconnect()
        await api.connect()
    assert factory.call_args_list[0].args[0] is first
    assert factory.call_args_list[1].args[0] is second
    assert len(controllers) == 2


async def test_legacy_start_sequence(api_and_controller):
    """Keep manual mode selection for previously supported WiLink pads."""
    api, controller = api_and_controller
    controller.protocol = ProtocolType.WILINK
    await api.start_belt()
    controller.switch_mode.assert_awaited_once_with(OperatingMode.MANUAL)
    controller.start.assert_awaited_once()
    controller.update_state.assert_awaited_once()
