"""Expose deliberate one-shot WalkingPad actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import WalkingPadCoordinator
from .device_profile import Capability
from .entity import WalkingPadEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up WalkingPad action buttons."""
    coordinator = entry.runtime_data
    if coordinator.api.profile.supports(Capability.SLEEP):
        async_add_entities([WalkingPadSleepButton(coordinator)])


class WalkingPadSleepButton(WalkingPadEntity, ButtonEntity):
    """Put the stopped WalkingPad into low-power sleep mode."""

    _attr_translation_key = "sleep"
    _attr_icon = "mdi:power-sleep"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the sleep button with a stable unique ID."""
        super().__init__(coordinator, "sleep")

    async def async_press(self) -> None:
        """Stop the belt if necessary, then enter sleep mode."""
        await self.coordinator.api.sleep()
