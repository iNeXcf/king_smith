"""Set WalkingPad speed in kilometers per hour."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import WalkingPadCoordinator
from .device_profile import Capability
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the speed control."""
    coordinator = entry.runtime_data
    if coordinator.api.profile.supports(Capability.SPEED_CONTROL):
        async_add_entities(
            [WalkingPadSpeed(coordinator), WalkingPadSpeedAdjustmentStep(coordinator)]
        )


class WalkingPadSpeed(WalkingPadEntity, NumberEntity):
    """Control speed using the device's supported range and increment."""

    _attr_translation_key = "speed"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the speed entity."""
        super().__init__(coordinator, "speed")
        self._attr_native_min_value = coordinator.api.min_speed
        self._attr_native_max_value = coordinator.api.max_speed
        self._attr_native_step = coordinator.api.speed_increment

    @property
    def native_value(self) -> float | None:
        """Return actual running speed, keeping a valid stopped slider value."""
        speed = self.coordinator.api.speed
        return max(self.native_min_value, speed) if speed is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set speed in the same 0.1 km/h increments as KS Fit."""
        await self.coordinator.api.change_speed(value)
        await self.coordinator.async_request_refresh()


class WalkingPadSpeedAdjustmentStep(WalkingPadEntity, RestoreEntity, NumberEntity):
    """Configure how much the speed buttons change the target speed."""

    _attr_translation_key = "speed_adjustment_step"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0.1
    _attr_native_max_value = 1.0
    _attr_native_step = 0.1
    _attr_icon = "mdi:delta"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the local speed adjustment setting."""
        super().__init__(coordinator, "speed_adjustment_step")

    @property
    def native_value(self) -> float:
        """Return the configured button adjustment step."""
        return self.coordinator.api.speed_adjustment_step

    async def async_added_to_hass(self) -> None:
        """Restore the adjustment step across Home Assistant restarts."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            try:
                value = float(state.state)
            except ValueError:
                return
            if self.native_min_value <= value <= self.native_max_value:
                self.coordinator.api.speed_adjustment_step = value

    async def async_set_native_value(self, value: float) -> None:
        """Set the step used by the speed-up and speed-down buttons."""
        self.coordinator.api.speed_adjustment_step = round(value, 1)
        self.async_write_ha_state()
