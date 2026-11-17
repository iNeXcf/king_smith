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
    entities: list[ButtonEntity] = []
    if coordinator.api.profile.supports(Capability.SPEED_CONTROL):
        entities.extend(
            [WalkingPadSpeedDownButton(coordinator), WalkingPadSpeedUpButton(coordinator)]
        )
    if coordinator.api.profile.supports(Capability.SLEEP):
        entities.append(WalkingPadSleepButton(coordinator))
    async_add_entities(entities)


class WalkingPadSpeedDownButton(WalkingPadEntity, ButtonEntity):
    """Reduce the target speed by the configured adjustment step."""

    _attr_translation_key = "speed_down"
    _attr_icon = "mdi:minus"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the speed-down button with a stable unique ID."""
        super().__init__(coordinator, "speed_down")

    async def async_press(self) -> None:
        """Reduce the current speed."""
        await self.coordinator.api.adjust_speed(-1)


class WalkingPadSpeedUpButton(WalkingPadEntity, ButtonEntity):
    """Increase the target speed by the configured adjustment step."""

    _attr_translation_key = "speed_up"
    _attr_icon = "mdi:plus"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        """Initialize the speed-up button with a stable unique ID."""
        super().__init__(coordinator, "speed_up")

    async def async_press(self) -> None:
        """Increase the current speed."""
        await self.coordinator.api.adjust_speed(1)


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
