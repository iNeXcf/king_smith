"""Exercise the real FTMS backend using simulated GATT responses."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from walkingpad_controller.const import FTMS_CONTROL_POINT_UUID, TREADMILL_DATA_UUID

from custom_components.king_smith.ftms import (
    KingsmithController,
    KingsmithFTMSController,
    SUPPLEMENT_NOTIFY_UUID,
    SUPPLEMENT_WRITE_UUID,
)


def test_treadmill_packet():
    """Decode speed, distance, duration, and the two-byte Z1 step counter."""
    controller = KingsmithFTMSController("KS-HD-Z1D")
    callback = MagicMock()
    controller.register_status_callback(callback)
    packet = bytes.fromhex("0424 4a01 e80300 7800 c800")
    controller._on_treadmill_data(1, bytearray(packet))
    assert controller.status.speed == 3.3
    assert controller.status.distance == 1000
    assert controller.status.duration == 120
    assert controller.status.steps == 200
    callback.assert_called_once()
    controller._on_treadmill_data(1, bytearray(packet + b"\x00"))
    assert controller.status.steps == 200


@pytest.mark.parametrize(
    "packet", [b"", b"\x00", b"\x00\x00\x01", bytes.fromhex("0424 4a01 e80300 7800 c8")]
)
def test_incomplete_packets_are_ignored(packet):
    """Keep valid device state intact when a notification is truncated."""
    controller = KingsmithFTMSController("KS-HD-Z1D")
    callback = MagicMock()
    controller.register_status_callback(callback)
    controller._on_treadmill_data(1, bytearray(packet))
    callback.assert_not_called()


def test_more_data_retains_speed():
    """Parse a continuation notification whose speed field is absent."""
    controller = KingsmithFTMSController("KS-HD-Z1D")
    controller._on_treadmill_data(1, bytearray.fromhex("0000 4a01"))
    controller._on_treadmill_data(1, bytearray.fromhex("0500 e80300"))
    assert controller.status.speed == 3.3
    assert controller.status.distance == 1000


async def test_z1_unlock_precedes_ftms_subscriptions():
    """Initialize a real backend through a simulated BLE client."""
    controller = KingsmithFTMSController("KS-HD-Z1D")
    client = MagicMock()
    client.is_connected = True
    client.services = MagicMock()
    client.start_notify = AsyncMock()
    client.disconnect = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=b"")

    async def write(uuid, data, **kwargs):
        if uuid == SUPPLEMENT_WRITE_UUID:
            assert data.hex() == "710005012e5a314474"
            assert kwargs == {"response": False}
            assert (
                client.start_notify.call_args_list[0].args[0] == SUPPLEMENT_NOTIFY_UUID
            )
            controller._on_supplement(1, bytearray.fromhex("718000f1"))
        elif uuid == FTMS_CONTROL_POINT_UUID:
            controller._cp_response_data = bytes([0x80, data[0], 1])
            controller._cp_response_event.set()

    client.write_gatt_char = AsyncMock(side_effect=write)
    with patch(
        "walkingpad_controller.ftms.establish_connection",
        AsyncMock(return_value=client),
    ):
        await controller.connect(BLEDevice("AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", {}))
    assert controller.connected
    assert controller._unlock_event.is_set()
    assert TREADMILL_DATA_UUID in [
        call.args[0] for call in client.start_notify.call_args_list
    ]
    assert await controller.stop()
    await controller.disconnect()
    client.disconnect.assert_awaited_once()


async def test_unlock_failure_closes_client():
    """Tear down a client when supplement initialization fails."""
    controller = KingsmithController(BLEDevice("AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", {}))
    with (
        patch.object(
            KingsmithFTMSController,
            "connect",
            AsyncMock(side_effect=BleakError("unlock failed")),
        ),
        patch.object(KingsmithFTMSController, "disconnect", AsyncMock()) as disconnect,
        pytest.raises(BleakError),
    ):
        await controller.connect()
    disconnect.assert_awaited_once()


def test_invalid_unlock_checksum():
    """Require a complete, correctly checksummed unlock acknowledgement."""
    controller = KingsmithFTMSController("KS-HD-Z1D")
    for value in ["7180", "71800000", "718005f1"]:
        controller._on_supplement(1, bytearray.fromhex(value))
    assert not controller._unlock_event.is_set()


def test_missing_optional_fields_remain_unknown():
    """Keep absent FTMS fields distinct from actual zero counters."""
    from custom_components.king_smith.walking_pad import WalkingPadApi

    controller = KingsmithFTMSController("KS-HD-Z1D")
    api = WalkingPadApi("Z1", "AA:BB:CC:DD:EE:FF", "KS-HD-Z1D", MagicMock())
    controller.register_status_callback(api._on_status_update)
    controller._on_treadmill_data(1, bytearray.fromhex("0000 4a01"))
    assert api.speed == 3.3
    assert api.distance is None
    assert api.time is None
    assert api.steps is None
    assert api.step_cadence is None
    controller._on_treadmill_data(1, bytearray.fromhex("0424 4a01 e80300 7800 c800"))
    assert api.distance == 1.0
    assert api.steps == 200


def test_bad_unlock_checksum_is_rejected():
    """Wait for a valid supplement response instead of accepting corruption."""
    controller = KingsmithFTMSController("KS-HD-Z1D")
    controller._on_supplement(1, bytearray.fromhex("71800000"))
    assert not controller._unlock_event.is_set()
    controller._on_supplement(1, bytearray.fromhex("718000f1"))
    assert controller._unlock_event.is_set()
