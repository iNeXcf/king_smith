"""Expose session measurements and restore accumulated totals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfSpeed, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WalkingPadSensorDescription(SensorEntityDescription):
    """Describe a measurement and its source property."""

    property_name: str
    accumulated: bool = False


SENSORS = (
    WalkingPadSensorDescription(
        key="distance",
        property_name="distance",
        translation_key="distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    WalkingPadSensorDescription(
        key="time",
        property_name="time",
        translation_key="duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    WalkingPadSensorDescription(
        key="speed",
        property_name="speed",
        translation_key="speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WalkingPadSensorDescription(
        key="steps",
        property_name="steps",
        translation_key="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:walk",
    ),
    WalkingPadSensorDescription(
        key="step_cadence",
        property_name="step_cadence",
        translation_key="step_cadence",
        native_unit_of_measurement="steps/min",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:walk",
    ),
    WalkingPadSensorDescription(
        key="total_distance",
        property_name="distance",
        translation_key="total_distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        accumulated=True,
    ),
    WalkingPadSensorDescription(
        key="total_time",
        property_name="time",
        translation_key="total_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        accumulated=True,
    ),
    WalkingPadSensorDescription(
        key="total_steps",
        property_name="steps",
        translation_key="total_steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:walk",
        accumulated=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up all measurement entities."""
    async_add_entities(
        [
            WalkingPadTotalSensor(entry.runtime_data, description)
            if description.accumulated
            else WalkingPadSensor(entry.runtime_data, description)
            for description in SENSORS
        ]
    )


class WalkingPadSensor(WalkingPadEntity, SensorEntity):
    """Read a session measurement from the common device state."""

    entity_description: WalkingPadSensorDescription

    def __init__(
        self,
        coordinator: WalkingPadCoordinator,
        description: WalkingPadSensorDescription,
    ) -> None:
        """Initialize the measurement using its existing unique ID suffix."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return a value only after the first actual device report."""
        if self.coordinator.api.status is None:
            return None
        return getattr(self.coordinator.api, self.entity_description.property_name)


class WalkingPadTotalSensor(WalkingPadSensor, RestoreSensor):
    """Accumulate session deltas and persist the last counter baseline."""

    def __init__(
        self,
        coordinator: WalkingPadCoordinator,
        description: WalkingPadSensorDescription,
    ) -> None:
        """Initialize total and baseline state."""
        super().__init__(coordinator, description)
        self._total = 0
        self._last: float | int | None = 0
        self._last_duration = 0
        self._restored = False

    @property
    def native_value(self) -> float | int:
        """Return the accumulated total."""
        return self._total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Store the device counters used to avoid counting a session twice."""
        return {
            "last_session_value": self._last,
            "last_session_duration": self._last_duration,
        }

    async def async_added_to_hass(self) -> None:
        """Restore the total and baseline before applying current counters."""
        await super().async_added_to_hass()
        if (sensor_data := await self.async_get_last_sensor_data()) is not None:
            self._total = sensor_data.native_value or 0
            # Older versions only persisted the total. Start their baseline
            # at the current device value to avoid adding the session again.
            self._last = None
            if (state := await self.async_get_last_state()) is not None:
                self._last = state.attributes.get("last_session_value")
                self._last_duration = state.attributes.get("last_session_duration", 0)
        self._restored = True
        self._accumulate()

    def _accumulate(self) -> None:
        """Add the difference from the last known device counter."""
        api = self.coordinator.api
        value = getattr(api, self.entity_description.property_name)
        if value is None or not self._restored:
            return
        duration = api.time
        if self._last is not None:
            if (
                duration is not None and duration < self._last_duration
            ) or value < self._last:
                self._total += value
            else:
                self._total += value - self._last
        self._last = value
        if duration is not None:
            self._last_duration = duration

    @callback
    def _handle_coordinator_update(self) -> None:
        """Accumulate each device report before writing state."""
        self._accumulate()
        self.async_write_ha_state()
