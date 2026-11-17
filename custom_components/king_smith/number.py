"""Set WalkingPad speed in kilometers per hour."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
        async_add_entities([WalkingPadSpeed(coordinator)])


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
