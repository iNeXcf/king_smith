"""Use a real Home Assistant event loop with isolated in-memory storage."""

from types import MappingProxyType
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from homeassistant import loader
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util.executor import InterruptibleThreadPoolExecutor
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    frame,
    restore_state,
)


@pytest_asyncio.fixture
async def hass(tmp_path):
    """Create Home Assistant with empty storage and real registries."""
    with patch(
        "homeassistant.helpers.storage.Store.async_load", AsyncMock(return_value=None)
    ), patch.object(
        HomeAssistant, "async_add_executor_job", run_executor_job
    ), patch.object(HomeAssistant, "async_add_import_executor_job", run_executor_job):
        instance = HomeAssistant(str(tmp_path))
        executor = InterruptibleThreadPoolExecutor(max_workers=2)
        instance.loop.set_default_executor(executor)
        loader.async_setup(instance)
        frame.async_setup(instance)
        instance.config_entries = ConfigEntries(instance, {})
        await instance.config_entries.async_initialize()
        dr.async_setup(instance)
        await dr.async_load(instance, load_empty=True)
        await er.async_load(instance, load_empty=True)
        await restore_state.async_load(instance, load_empty=True)
        yield instance
        await instance.async_stop(force=True)
        instance.import_executor.shutdown()
        executor.shutdown()


def run_executor_job(hass, target, *args):
    """Run local file imports synchronously inside the isolated test loop."""
    future = hass.loop.create_future()
    try:
        future.set_result(target(*args))
    except Exception as error:
        future.set_exception(error)
    return future


@pytest.fixture
def entry():
    """Create a real config entry with the confirmed Z1 name."""
    return ConfigEntry(
        domain="king_smith",
        title="WalkingPad Z1",
        version=1,
        minor_version=1,
        data={
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "WalkingPad Z1",
            "ble_name": "KS-HD-Z1D",
        },
        options={},
        source="user",
        unique_id="aa:bb:cc:dd:ee:ff",
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )
