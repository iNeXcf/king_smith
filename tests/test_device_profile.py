"""Verify model matching, capabilities, and legacy config compatibility."""

from custom_components.king_smith.device_profile import (
    Capability,
    LEGACY_WILINK_PROFILE,
    Z1_PROFILE,
    profile_for_name,
    resolve_profile,
)


def test_z1_profile_describes_safe_controls():
    """Keep Z1 limits and proprietary features in one data object."""
    assert profile_for_name("KS-HD-Z1D") is Z1_PROFILE
    assert Z1_PROFILE.min_speed == 1.0
    assert Z1_PROFILE.max_speed == 6.0
    assert Z1_PROFILE.speed_step == 0.1
    assert Z1_PROFILE.supports(Capability.SPEED_CONTROL)
    assert Z1_PROFILE.supports(Capability.SLEEP)
    assert Z1_PROFILE.supplement_unlock


def test_old_config_entry_is_resolved_from_ble_name():
    """Do not require users to recreate entries made before profiles existed."""
    assert resolve_profile(None, "KS-HD-Z1D") is Z1_PROFILE
    assert resolve_profile(None, "KS-BL-TM") is LEGACY_WILINK_PROFILE


def test_saved_profile_wins_over_changed_advertised_name():
    """Keep a configured model stable if firmware changes its local name."""
    assert resolve_profile("z1", "unexpected") is Z1_PROFILE
