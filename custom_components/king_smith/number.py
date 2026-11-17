"""Set WalkingPad speed in kilometers per hour."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the speed control."""
    async_add_entities([WalkingPadSpeed(entry.runtime_data)])


class WalkingPadSpeed(WalkingPadEntity, NumberEntity):
    """Control speed using the device's supported range and increment."""

    _attr_translation_key = "speed"
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0.0

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the speed entity."""
        super().__init__(coordinator, "speed")

    @property
    def native_max_value(self) -> float:
        """Return the device's maximum speed."""
        return self.coordinator.api.max_speed

    @property
    def native_step(self) -> float:
        """Return the device's speed increment."""
        return self.coordinator.api.speed_increment

    @property
    def native_value(self) -> float | None:
        """Return actual speed reported by the belt."""
        return self.coordinator.api.speed

    async def async_set_native_value(self, value: float) -> None:
        """Set speed, with zero meaning stop."""
        await self.coordinator.api.change_speed(value)
        await self.coordinator.async_request_refresh()
