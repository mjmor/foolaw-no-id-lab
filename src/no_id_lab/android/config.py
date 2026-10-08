"""Declarative Android lab configuration loaded from configs/android/lab.yaml."""

from __future__ import annotations

import dataclasses
import platform
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

IMAGE_TAGS = ("default", "google_apis", "google_apis_playstore")
ARCHITECTURES = ("auto", "arm64-v8a", "x86_64")
SDK_PATH_POLICIES = ("project", "env")
BOOT_MODES = ("cold", "quick")
HOST_ABIS = {"arm64": "arm64-v8a", "aarch64": "arm64-v8a", "x86_64": "x86_64", "amd64": "x86_64"}
AVD_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ConfigError(ValueError):
    pass


def resolve_abi(architecture: str, machine: str | None = None) -> str:
    if architecture != "auto":
        if architecture not in ARCHITECTURES:
            raise ConfigError(f"system_image.architecture must be one of {ARCHITECTURES}, got {architecture!r}")
        return architecture
    machine = (machine or platform.machine()).lower()
    try:
        return HOST_ABIS[machine]
    except KeyError:
        raise ConfigError(f"Unsupported host architecture {machine!r}; set system_image.architecture explicitly") from None


@dataclass(frozen=True)
class LabConfig:
    api_level: int
    image_tag: str
    architecture: str
    device_profile: str
    avd_name: str
    headless: bool
    sdk_path_policy: str
    lab_home: str
    cmdline_tools_version: str
    sdk_packages: tuple[str, ...]
    sdcard_size: str
    hardware: dict[str, str] = field(default_factory=dict)
    console_port: int = 5554
    boot_mode: str = "cold"
    gpu: str = "auto"
    headless_gpu: str = "swiftshader_indirect"
    boot_timeout_seconds: float = 420
    stop_timeout_seconds: float = 60
    poll_interval_seconds: float = 2
    boot_attempts: int = 2

    def __post_init__(self) -> None:
        _choice("system_image.tag", self.image_tag, IMAGE_TAGS)
        _choice("system_image.architecture", self.architecture, ARCHITECTURES)
        _choice("sdk.path_policy", self.sdk_path_policy, SDK_PATH_POLICIES)
        _choice("emulator.boot_mode", self.boot_mode, BOOT_MODES)
        if not AVD_NAME_PATTERN.match(self.avd_name):
            raise ConfigError(f"avd_name must match {AVD_NAME_PATTERN.pattern}, got {self.avd_name!r}")
        if not (5554 <= self.console_port <= 5682 and self.console_port % 2 == 0):
            raise ConfigError("emulator.console_port must be an even number between 5554 and 5682")
        if self.boot_attempts < 1:
            raise ConfigError("retries.boot_attempts must be at least 1")
        for name in ("boot_timeout_seconds", "stop_timeout_seconds", "poll_interval_seconds"):
            if getattr(self, name) <= 0:
                raise ConfigError(f"timeouts.{name.removesuffix('_seconds')}_seconds must be positive")

    @property
    def serial(self) -> str:
        return f"emulator-{self.console_port}"

    def abi(self, machine: str | None = None) -> str:
        return resolve_abi(self.architecture, machine)

    def system_image_package(self, machine: str | None = None) -> str:
        """Semicolon form, as avdmanager expects."""
        return f"system-images;android-{self.api_level};{self.image_tag};{self.abi(machine)}"

    def system_image_dir(self, machine: str | None = None) -> str:
        return f"system-images/android-{self.api_level}/{self.image_tag}/{self.abi(machine)}/"

    def required_packages(self, machine: str | None = None) -> list[str]:
        """SDK package paths in the `android sdk` CLI's slash-separated form."""
        return [
            f"cmdline-tools/{self.cmdline_tools_version}",
            *self.sdk_packages,
            self.system_image_package(machine).replace(";", "/"),
        ]

    def with_overrides(self, **changes: Any) -> LabConfig:
        return dataclasses.replace(self, **changes)


def load_config(path: Path) -> LabConfig:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read Android lab config {path}: {exc}") from exc

    def get(dotted: str, default: Any = ...) -> Any:
        node: Any = data
        for key in dotted.split("."):
            if not isinstance(node, dict) or key not in node:
                if default is ...:
                    raise ConfigError(f"Missing required setting {dotted!r} in {path}")
                return default
            node = node[key]
        return node

    try:
        return LabConfig(
            api_level=int(get("api_level")),
            image_tag=str(get("system_image.tag")),
            architecture=str(get("system_image.architecture", "auto")),
            device_profile=str(get("device_profile")),
            avd_name=str(get("avd_name")),
            headless=bool(get("headless", False)),
            sdk_path_policy=str(get("sdk.path_policy", "project")),
            lab_home=str(get("sdk.lab_home", ".android-lab")),
            cmdline_tools_version=str(get("sdk.cmdline_tools_version")),
            sdk_packages=tuple(str(p) for p in get("sdk.packages", ["platform-tools", "emulator"])),
            sdcard_size=str(get("avd.sdcard_size", "512M")),
            hardware={str(k): _ini_value(v) for k, v in (get("avd.hardware", {}) or {}).items()},
            console_port=int(get("emulator.console_port", 5554)),
            boot_mode=str(get("emulator.boot_mode", "cold")),
            gpu=str(get("emulator.gpu", "auto")),
            headless_gpu=str(get("emulator.headless_gpu", "swiftshader_indirect")),
            boot_timeout_seconds=float(get("timeouts.boot_seconds", 420)),
            stop_timeout_seconds=float(get("timeouts.stop_seconds", 60)),
            poll_interval_seconds=float(get("timeouts.poll_interval_seconds", 2)),
            boot_attempts=int(get("retries.boot_attempts", 2)),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ConfigError):
            raise
        raise ConfigError(f"Invalid Android lab config {path}: {exc}") from exc


def _choice(name: str, value: str, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise ConfigError(f"{name} must be one of {allowed}, got {value!r}")


def _ini_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)
