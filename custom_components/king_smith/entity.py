"""Shared WalkingPad entity identity and availability."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WalkingPadCoordinator


class WalkingPadEntity(CoordinatorEntity[WalkingPadCoordinator]):
    """Represent one entity of a centrally managed treadmill."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WalkingPadCoordinator, key: str) -> None:
        """Keep existing unique ID suffixes and let HA assign entity IDs."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.api.mac}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Identify the shared treadmill device."""
        api = self.coordinator.api
        return DeviceInfo(
            identifiers={(DOMAIN, api.mac)},
            manufacturer="King Smith",
            name=api.name,
            sw_version=api.firmware_version,
        )

    @property
    def available(self) -> bool:
        """Reflect both update failures and the live BLE connection."""
        return super().available and self.coordinator.api.connected
