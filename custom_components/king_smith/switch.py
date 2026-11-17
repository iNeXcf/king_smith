"""Control the WalkingPad belt."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the belt switch."""
    async_add_entities([WalkingPadSwitch(entry.runtime_data)])


class WalkingPadSwitch(WalkingPadEntity, SwitchEntity):
    """Start and stop the belt using device-reported state."""

    _attr_name = None
    _attr_icon = "mdi:walk"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the belt switch."""
        super().__init__(coordinator, "switch")

    @property
    def is_on(self) -> bool | None:
        """Return the last reported movement state."""
        return self.coordinator.api.moving

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the treadmill."""
        await self.coordinator.api.start_belt()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the treadmill and finish the session."""
        await self.coordinator.api.stop_belt()
        await self.coordinator.async_request_refresh()
