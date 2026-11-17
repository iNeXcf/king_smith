"""Verify totals across HA restarts and device session resets."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorExtraStoredData
from homeassistant.core import State
from walkingpad_controller.models import TreadmillStatus

from custom_components.king_smith.coordinator import WalkingPadCoordinator
from custom_components.king_smith.sensor import SENSORS, WalkingPadTotalSensor
from custom_components.king_smith.walking_pad import WalkingPadApi


@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("total_steps", 320, 1020),
        ("total_time", 320, 1020),
        ("total_distance", 3200, 1000.2),
    ],
)
async def test_restore_counts_only_new_data(hass, entry, key, value, expected):
    """Retain the persisted baseline when HA restarts during a session."""
    api = WalkingPadApi("Z1", "AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", MagicMock())
    api.disconnect = AsyncMock()
    report = TreadmillStatus(steps=320, duration=320, distance=3200)
    api._on_status_update(report)
    coordinator = WalkingPadCoordinator(hass, entry, api, "device")
    description = next(description for description in SENSORS if description.key == key)
    sensor = WalkingPadTotalSensor(coordinator, description)
    sensor.hass = hass
    sensor.platform = SimpleNamespace(
        platform_name="king_smith", config_entry=entry, domain="sensor"
    )
    sensor.entity_id = f"sensor.{key}"
    baseline = 3.0 if key == "total_distance" else 300
    stored = SensorExtraStoredData(1000, description.native_unit_of_measurement)
    state = State(
        sensor.entity_id,
        "1000",
        {"last_session_value": baseline, "last_session_duration": 300},
    )
    await sensor.async_internal_added_to_hass()
    with patch.object(
        sensor, "async_get_last_sensor_data", AsyncMock(return_value=stored)
    ), patch.object(sensor, "async_get_last_state", AsyncMock(return_value=state)):
        await sensor.async_added_to_hass()
    assert sensor.native_value == pytest.approx(expected)
    sensor._accumulate()
    assert sensor.native_value == pytest.approx(expected)
    await sensor.async_internal_will_remove_from_hass()
    await coordinator.async_shutdown()


async def test_legacy_restore_has_no_duplicate_session(hass, entry):
    """Upgrade totals that were persisted without a session baseline."""
    api = WalkingPadApi("Z1", "AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", MagicMock())
    api.disconnect = AsyncMock()
    api._on_status_update(TreadmillStatus(steps=300, duration=100))
    coordinator = WalkingPadCoordinator(hass, entry, api, "device")
    description = next(
        description for description in SENSORS if description.key == "total_steps"
    )
    sensor = WalkingPadTotalSensor(coordinator, description)
    sensor.hass = hass
    sensor.platform = SimpleNamespace(
        platform_name="king_smith", config_entry=entry, domain="sensor"
    )
    sensor.entity_id = "sensor.total_steps"
    await sensor.async_internal_added_to_hass()
    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        AsyncMock(return_value=SensorExtraStoredData(1000, None)),
    ), patch.object(
        sensor,
        "async_get_last_state",
        AsyncMock(return_value=State(sensor.entity_id, "1000")),
    ):
        await sensor.async_added_to_hass()
    assert sensor.native_value == 1000
    api.status = TreadmillStatus(steps=320, duration=110)
    sensor._accumulate()
    assert sensor.native_value == 1020
    api.status = TreadmillStatus(steps=400, duration=20)
    sensor._accumulate()
    assert sensor.native_value == 1420
    await sensor.async_internal_will_remove_from_hass()
    await coordinator.async_shutdown()
