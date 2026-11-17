"""Set up the KingSmith WalkingPad integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_BLE_NAME, DOMAIN
from .coordinator import WalkingPadCoordinator
from .walking_pad import WalkingPadApi

PLATFORMS = [Platform.BUTTON, Platform.SWITCH, Platform.NUMBER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect once before creating entities for the treadmill."""
    address = entry.data[CONF_MAC]
    name = entry.data.get(CONF_NAME, "WalkingPad")
    api = WalkingPadApi(
        name,
        address,
        entry.data.get(CONF_BLE_NAME, ""),
        lambda: bluetooth.async_ble_device_from_address(
            hass, address, connectable=True
        ),
    )
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, address)},
        name=name,
        manufacturer="King Smith",
    )
    coordinator = WalkingPadCoordinator(hass, entry, api, device.id)
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_shutdown()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload entities and release all connection resources."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_shutdown()
    bluetooth.async_rediscover_address(hass, entry.data[CONF_MAC])
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate entries created with the original fractional flow version."""
    if entry.version > 1:
        return False
    hass.config_entries.async_update_entry(entry, version=1, minor_version=1)
    return True
