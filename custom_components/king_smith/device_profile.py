"""Describe model-specific King Smith capabilities without protocol branching."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fnmatch import fnmatchcase


class Capability(StrEnum):
    """Optional controls exposed by a WalkingPad profile."""

    SPEED_CONTROL = "speed_control"
    SLEEP = "sleep"


class SleepStrategy(StrEnum):
    """Known ways to put a WalkingPad into low-power mode."""

    STANDBY = "standby"
    Z1_PROPERTY = "z1_property"


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    """Static characteristics that cannot be discovered safely over Bluetooth."""

    profile_id: str
    model: str
    name_patterns: tuple[str, ...]
    capabilities: frozenset[Capability]
    min_speed: float | None = None
    max_speed: float | None = None
    speed_step: float | None = None
    sleep_strategy: SleepStrategy | None = None
    supplement_unlock: bool = False
    anonymous_ftms_name: str | None = None

    def matches_name(self, name: str) -> bool:
        """Return whether an advertised name identifies this profile."""
        return any(fnmatchcase(name, pattern) for pattern in self.name_patterns)

    def supports(self, capability: Capability) -> bool:
        """Return whether this model safely supports a feature."""
        return capability in self.capabilities


Z1_PROFILE = DeviceProfile(
    profile_id="z1",
    model="WalkingPad Z1",
    name_patterns=("KS-HD-Z1D*",),
    capabilities=frozenset({Capability.SPEED_CONTROL, Capability.SLEEP}),
    min_speed=1.0,
    max_speed=6.0,
    speed_step=0.1,
    sleep_strategy=SleepStrategy.Z1_PROPERTY,
    supplement_unlock=True,
    anonymous_ftms_name="KS-HD-Z1D",
)

LEGACY_WILINK_PROFILE = DeviceProfile(
    profile_id="legacy_wilink",
    model="WalkingPad",
    name_patterns=("KS-BL*", "KS-ST-*", "WalkingPad"),
    capabilities=frozenset({Capability.SPEED_CONTROL, Capability.SLEEP}),
    sleep_strategy=SleepStrategy.STANDBY,
)

DEVICE_PROFILES = (Z1_PROFILE, LEGACY_WILINK_PROFILE)
PROFILES_BY_ID = {profile.profile_id: profile for profile in DEVICE_PROFILES}


def profile_for_name(name: str) -> DeviceProfile | None:
    """Find a profile from a Bluetooth local name."""
    return next((profile for profile in DEVICE_PROFILES if profile.matches_name(name)), None)


def resolve_profile(profile_id: str | None, ble_name: str) -> DeviceProfile:
    """Resolve saved entries and remain compatible with entries from older releases."""
    if profile_id and (profile := PROFILES_BY_ID.get(profile_id)) is not None:
        return profile
    if profile := profile_for_name(ble_name):
        return profile
    return LEGACY_WILINK_PROFILE
