"""Configure a WalkingPad through discovery or manual device selection."""

from __future__ import annotations

from fnmatch import fnmatchcase
import re
from typing import Any

import probatio
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_BLE_NAME, DOMAIN

NAME_PATTERNS = ("KS-BL*", "KS-ST-*", "WalkingPad", "KS-HD-Z1D*")
FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"


def _advertised_names(info: Any) -> tuple[str, ...]:
    """Return every Bluetooth name exposed by HA and its scanner backend."""
    names: list[str] = []
    for candidate in (
        getattr(info, "name", None),
        getattr(getattr(info, "advertisement", None), "local_name", None),
        getattr(getattr(info, "raw", None), "local_name", None),
    ):
        if candidate and candidate not in names:
            names.append(candidate)
    return tuple(names)


def _supported_ble_name(info: Any) -> str | None:
    """Return the useful local name, also accepting anonymous FTMS adverts."""
    names = _advertised_names(info)
    for name in names:
        if any(fnmatchcase(name, pattern) for pattern in NAME_PATTERNS):
            return name
    service_uuids = {uuid.lower() for uuid in getattr(info, "service_uuids", ())}
    if FTMS_SERVICE_UUID in service_uuids or "1826" in service_uuids:
        # Some proxies omit the local name. The selected address is still a
        # connectable FTMS treadmill and Z1 needs this name for its unlock key.
        return "KS-HD-Z1D"
    return None


class WalkingpadConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle configuration of one WalkingPad."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize discovery data for all flow entry points."""
        self._address: str | None = None
        self._ble_name = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow configuration from Add integration."""
        return await self.async_step_device(user_input)

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Configure a device found by a connectable Bluetooth scanner."""
        if not discovery_info.connectable:
            return self.async_abort(reason="not_connectable")
        await self.async_set_unique_id(dr.format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address
        self._ble_name = _supported_ble_name(discovery_info) or discovery_info.name
        self.context["title_placeholders"] = {"name": self._ble_name}
        return await self.async_step_device()

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a discovered device or enter its Bluetooth address."""
        errors = {}
        if user_input is not None:
            address = dr.format_mac(user_input[CONF_MAC]).upper()
            name = user_input[CONF_NAME].strip()
            if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", address):
                errors[CONF_MAC] = "invalid_address"
            elif not name:
                errors[CONF_NAME] = "invalid_name"
            else:
                await self.async_set_unique_id(dr.format_mac(address))
                self._abort_if_unique_id_configured()
                info = bluetooth.async_last_service_info(
                    self.hass, address, connectable=True
                )
                if info is None:
                    errors["base"] = "device_not_found"
                elif (ble_name := _supported_ble_name(info)) is None:
                    errors["base"] = "unsupported_device"
                else:
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_MAC: address,
                            CONF_NAME: name,
                            CONF_BLE_NAME: ble_name,
                        },
                    )
        options = [
            {
                "value": info.address,
                "label": f"{_supported_ble_name(info)} ({info.address})",
            }
            for info in bluetooth.async_discovered_service_info(
                self.hass, connectable=True
            )
            if _supported_ble_name(info) is not None
        ]
        address_field = (
            probatio.Required(CONF_MAC, default=self._address)
            if self._address
            else probatio.Required(CONF_MAC)
        )
        return self.async_show_form(
            step_id="device",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_NAME, default=self._ble_name or "WalkingPad"
                    ): str,
                    address_field: SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            custom_value=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )
