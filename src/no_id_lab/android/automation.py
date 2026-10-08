"""Integration point for UI automation drivers (Appium/UiAutomator2).

Deliberately dependency-free: later phases add the Appium client and app-specific
capabilities, while the emulator target stays defined by the lab config.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .config import LabConfig

ANDROID_VERSIONS = {33: "13", 34: "14", 35: "15", 36: "16"}


@dataclass(frozen=True)
class DeviceTarget:
    serial: str
    avd_name: str
    api_level: int

    @classmethod
    def from_config(cls, config: LabConfig) -> DeviceTarget:
        return cls(serial=config.serial, avd_name=config.avd_name, api_level=config.api_level)

    def uiautomator2_capabilities(self, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
        caps: dict[str, Any] = {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:udid": self.serial,
            "appium:avd": self.avd_name,
        }
        if self.api_level in ANDROID_VERSIONS:
            caps["appium:platformVersion"] = ANDROID_VERSIONS[self.api_level]
        caps["appium:noReset"] = True
        caps.update(extra or {})
        return caps
