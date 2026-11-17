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
        self._ble_name = discovery_info.name
        self.context["title_placeholders"] = {"name": discovery_info.name}
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
                elif not any(
                    fnmatchcase(info.name, pattern) for pattern in NAME_PATTERNS
                ):
                    errors["base"] = "unsupported_device"
                else:
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_MAC: address,
                            CONF_NAME: name,
                            CONF_BLE_NAME: info.name,
                        },
                    )
        options = [
            {"value": info.address, "label": f"{info.name} ({info.address})"}
            for info in bluetooth.async_discovered_service_info(
                self.hass, connectable=True
            )
            if any(fnmatchcase(info.name, pattern) for pattern in NAME_PATTERNS)
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
