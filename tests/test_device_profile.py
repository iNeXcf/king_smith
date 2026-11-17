"""Verify model matching, capabilities, and legacy config compatibility."""

import pytest

from custom_components.king_smith.device_profile import (
    A1_PRO_PROFILE,
    Capability,
    LEGACY_WILINK_PROFILE,
    SleepStrategy,
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


@pytest.mark.parametrize("name", ["KS-ST-A1P", "KS-ST-A1P-1234"])
def test_a1_pro_profile_precedes_legacy_fallback(name):
    """Identify the A1 Pro before the broad KS-ST matcher."""
    assert profile_for_name(name) is A1_PRO_PROFILE
    assert A1_PRO_PROFILE.min_speed == 0.5
    assert A1_PRO_PROFILE.max_speed == 6.0
    assert A1_PRO_PROFILE.speed_step == 0.1
    assert A1_PRO_PROFILE.supports(Capability.SPEED_CONTROL)
    assert A1_PRO_PROFILE.supports(Capability.SLEEP)
    assert A1_PRO_PROFILE.sleep_strategy == SleepStrategy.STANDBY
    assert not A1_PRO_PROFILE.supplement_unlock
    assert A1_PRO_PROFILE.anonymous_ftms_name is None


def test_old_config_entry_is_resolved_from_ble_name():
    """Do not require users to recreate entries made before profiles existed."""
    assert resolve_profile(None, "KS-HD-Z1D") is Z1_PROFILE
    assert resolve_profile(None, "KS-BL-TM") is LEGACY_WILINK_PROFILE
    assert resolve_profile(None, "KS-ST-A1P") is A1_PRO_PROFILE
    assert resolve_profile(None, "KS-ST-OTHER") is LEGACY_WILINK_PROFILE


def test_saved_profile_wins_over_changed_advertised_name():
    """Keep a configured model stable if firmware changes its local name."""
    assert resolve_profile("z1", "unexpected") is Z1_PROFILE
    assert resolve_profile("a1_pro", "unexpected") is A1_PRO_PROFILE
    assert resolve_profile("legacy_wilink", "KS-ST-A1P") is LEGACY_WILINK_PROFILE
