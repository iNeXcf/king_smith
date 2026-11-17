"""Expose session events as Home Assistant device triggers."""

from __future__ import annotations

import probatio

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    EVENT_SESSION_DONE,
    EVENT_SESSION_START,
    SESSION_DONE,
    SESSION_START,
)

EVENTS = {SESSION_START: EVENT_SESSION_START, SESSION_DONE: EVENT_SESSION_DONE}
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {probatio.Required(CONF_TYPE): probatio.In(EVENTS)}
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List each supported session trigger once for this device."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None or not any(domain == DOMAIN for domain, _ in device.identifiers):
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: trigger_type,
        }
        for trigger_type in EVENTS
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Listen to the selected event for the selected device."""
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            CONF_PLATFORM: "event",
            "event_type": EVENTS[config[CONF_TYPE]],
            "event_data": {CONF_DEVICE_ID: config[CONF_DEVICE_ID]},
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
