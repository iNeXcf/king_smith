"""Coordinate one WalkingPad connection and its session events."""

from __future__ import annotations

from datetime import timedelta
import logging

from bleak.exc import BleakError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, ATTR_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from walkingpad_controller.const import BeltState
from walkingpad_controller.models import TreadmillStatus

from .const import DOMAIN, EVENT_SESSION_DONE, EVENT_SESSION_START
from .walking_pad import WalkingPadApi

_LOGGER = logging.getLogger(__name__)


class WalkingPadCoordinator(DataUpdateCoordinator[TreadmillStatus | None]):
    """Share notifications, connection maintenance, and session lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: WalkingPadApi,
        device_id: str,
    ) -> None:
        """Initialize one coordinator per treadmill."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
        )
        self.api = api
        self._device_id = device_id
        self._last_status: TreadmillStatus | None = None
        self._session_active = False
        self._remove_status = api.register_status_callback(self._handle_status)
        self._remove_disconnect = api.register_disconnect_callback(
            self._handle_disconnect
        )

    async def _async_update_data(self) -> TreadmillStatus | None:
        """Reconnect or poll through the common device queue."""
        try:
            return await self.api.update_state()
        except (BleakError, TimeoutError, RuntimeError) as error:
            raise UpdateFailed(str(error)) from error

    @callback
    def _handle_status(self, status: TreadmillStatus) -> None:
        """Publish device reports and derive session transitions."""
        previous = self._last_status
        if previous is None:
            self._session_active = (
                status.speed > 0 or status.belt_state == BeltState.PAUSED
            )
        else:
            reset = (
                getattr(status, "has_duration", True)
                and getattr(previous, "has_duration", True)
                and status.duration < previous.duration
            )
            stopped = (
                getattr(status, "has_speed", True)
                and previous.speed > 0
                and status.speed == 0
                and status.belt_state == BeltState.STOPPED
            )
            if self._session_active and (reset or stopped):
                final = previous if reset else status
                duration = final.duration
                data = {
                    "start_time": (
                        dt_util.utcnow() - timedelta(seconds=duration)
                    ).isoformat(),
                    "end_time": dt_util.utcnow().isoformat(),
                    "duration": duration,
                    "steps": final.steps,
                    "dist": final.distance / 1000,
                    "avg_step_cadence": final.steps * 60 / duration if duration else 0,
                    "avg_speed": final.distance * 3.6 / duration if duration else 0,
                }
                self._fire_event(EVENT_SESSION_DONE, data)
                self._session_active = False
            if not self._session_active and status.speed > 0:
                self._fire_event(
                    EVENT_SESSION_START,
                    {
                        "start_time": (
                            dt_util.utcnow() - timedelta(seconds=status.duration)
                        ).isoformat()
                    },
                )
                self._session_active = True
        self._last_status = status
        self.async_set_updated_data(status)

    @callback
    def _fire_event(self, event_type: str, data: dict) -> None:
        """Send JSON-serializable events tied to the device registry."""
        self.hass.bus.async_fire(
            event_type,
            {
                "identifiers": [[DOMAIN, self.api.mac]],
                ATTR_DEVICE_ID: self._device_id,
                ATTR_DOMAIN: DOMAIN,
                **data,
            },
        )

    @callback
    def _handle_disconnect(self) -> None:
        """Mark all entities unavailable until connection recovery."""
        self.async_set_update_error(UpdateFailed("Bluetooth connection lost"))

    async def async_shutdown(self) -> None:
        """Cancel updates and callbacks and release the connection."""
        if self._shutdown_requested:
            return
        self._remove_status()
        self._remove_disconnect()
        await super().async_shutdown()
        await self.api.disconnect()
