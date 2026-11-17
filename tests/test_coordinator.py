"""Check device events, disconnect availability, and cleanup."""

import json
from unittest.mock import AsyncMock, MagicMock

from walkingpad_controller.const import BeltState
from walkingpad_controller.models import TreadmillStatus

from custom_components.king_smith.const import EVENT_SESSION_DONE, EVENT_SESSION_START
from custom_components.king_smith.coordinator import WalkingPadCoordinator
from custom_components.king_smith.device_trigger import async_attach_trigger
from custom_components.king_smith.walking_pad import WalkingPadApi


async def test_session_events_drive_correct_device_trigger(hass, entry):
    """Deliver start and completion exactly once to the matching device."""
    api = WalkingPadApi("Z1", "AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", MagicMock())
    api.disconnect = AsyncMock()
    coordinator = WalkingPadCoordinator(hass, entry, api, "device-registry-id")
    events = []
    remove_start = hass.bus.async_listen(EVENT_SESSION_START, events.append)
    remove_done = hass.bus.async_listen(EVENT_SESSION_DONE, events.append)
    start_action = AsyncMock()
    done_action = AsyncMock()
    info = {"trigger_data": {"id": "0", "idx": "0", "alias": None}, "variables": {}}
    remove_start_trigger = await async_attach_trigger(
        hass,
        {"device_id": "device-registry-id", "type": "session_start"},
        start_action,
        info,
    )
    remove_done_trigger = await async_attach_trigger(
        hass,
        {"device_id": "device-registry-id", "type": "session_done"},
        done_action,
        info,
    )
    api._on_status_update(TreadmillStatus())
    api._on_status_update(TreadmillStatus(speed=3, duration=1, steps=2))
    api._on_status_update(TreadmillStatus(speed=3, duration=60, steps=100, distance=50))
    api._on_status_update(
        TreadmillStatus(
            speed=0, duration=60, steps=100, distance=50, belt_state=BeltState.STOPPED
        )
    )
    api._on_status_update(TreadmillStatus())
    hass.bus.async_fire(EVENT_SESSION_START, {"device_id": "other-device"})
    await hass.async_block_till_done()
    assert start_action.await_count == 1
    assert done_action.await_count == 1
    matching = [
        event for event in events if event.data["device_id"] == "device-registry-id"
    ]
    assert [event.event_type for event in matching] == [
        EVENT_SESSION_START,
        EVENT_SESSION_DONE,
    ]
    assert matching[-1].data["steps"] == 100
    assert matching[-1].data["dist"] == 0.05
    json.dumps(matching[-1].data)
    remove_start_trigger()
    remove_done_trigger()
    remove_start()
    remove_done()
    await coordinator.async_shutdown()
    await coordinator.async_shutdown()
    assert api._callbacks == []
    assert api._disconnect_callbacks == []
    api.disconnect.assert_awaited_once()


async def test_pause_preserves_session(hass, entry):
    """Keep a paused FTMS session active through its resume."""
    api = WalkingPadApi("Z1", "AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", MagicMock())
    api.disconnect = AsyncMock()
    coordinator = WalkingPadCoordinator(hass, entry, api, "device")
    events = []
    remove = hass.bus.async_listen(EVENT_SESSION_DONE, events.append)
    api._on_status_update(TreadmillStatus(speed=3, duration=60))
    api._on_status_update(
        TreadmillStatus(speed=0, duration=60, belt_state=BeltState.PAUSED)
    )
    api._on_status_update(TreadmillStatus(speed=3, duration=61))
    await hass.async_block_till_done()
    assert events == []
    api._on_disconnect()
    assert not coordinator.last_update_success
    remove()
    await coordinator.async_shutdown()
