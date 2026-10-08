"""In-scope app catalog (configs/android/apps.yaml) and per-app device helpers."""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .adb import Adb
from .config import ConfigError

PACKAGE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
VERSION_NAME = re.compile(r"versionName=(\S+)")
VERSION_CODE = re.compile(r"versionCode=(\d+)")
TIME_WINDOWS = (
    (6, 9, "morning"),
    (9, 15, "school_hours"),
    (15, 18, "after_school"),
    (18, 22, "evening"),
)


@dataclass(frozen=True)
class AppSpec:
    id: str
    name: str
    package: str


@dataclass(frozen=True)
class AppsConfig:
    apps: tuple[AppSpec, ...]
    install_timeout_seconds: float = 900
    install_poll_interval_seconds: float = 5
    record_seconds: int = 20
    settle_seconds: float = 2
    bit_rate: str = "4M"
    timestamp_overlay: bool = True
    captures_dir: str = "captures"

    def select(self, ids: list[str] | None) -> list[AppSpec]:
        if not ids:
            return list(self.apps)
        known = {app.id for app in self.apps}
        unknown = [i for i in ids if i not in known]
        if unknown:
            raise ConfigError(f"unknown app id(s) {unknown}; choose from {sorted(known)}")
        return [app for app in self.apps if app.id in ids]

    def with_overrides(self, **changes: Any) -> AppsConfig:
        return dataclasses.replace(self, **changes)


def load_apps_config(path: Path) -> AppsConfig:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read apps config {path}: {exc}") from exc
    apps = []
    for entry in data.get("apps") or []:
        package = str(entry.get("package", ""))
        if not PACKAGE_PATTERN.match(package):
            raise ConfigError(f"app {entry.get('id')!r} has an invalid package name {package!r}")
        apps.append(AppSpec(id=str(entry["id"]), name=str(entry.get("name", entry["id"])), package=package))
    if not apps:
        raise ConfigError(f"{path} must list at least one app")
    for field in ("id", "package"):
        values = [getattr(app, field) for app in apps]
        duplicates = sorted({v for v in values if values.count(v) > 1})
        if duplicates:
            raise ConfigError(f"duplicate app {field}(s) in {path}: {duplicates}")
    install = data.get("install") or {}
    recording = data.get("recording") or {}
    return AppsConfig(
        apps=tuple(apps),
        install_timeout_seconds=float(install.get("timeout_seconds", 900)),
        install_poll_interval_seconds=float(install.get("poll_interval_seconds", 5)),
        record_seconds=int(recording.get("seconds", 20)),
        settle_seconds=float(recording.get("settle_seconds", 2)),
        bit_rate=str(recording.get("bit_rate", "4M")),
        timestamp_overlay=bool(recording.get("timestamp_overlay", True)),
        captures_dir=str(recording.get("captures_dir", "captures")),
    )


@dataclass(frozen=True)
class AppInfo:
    installed: bool
    version_name: str | None = None
    version_code: str | None = None


def app_info(adb: Adb, serial: str, package: str) -> AppInfo:
    if not adb.shell(serial, "pm", "path", package, check=False).stdout.startswith("package:"):
        return AppInfo(installed=False)
    dump = adb.shell(serial, "dumpsys", "package", package, check=False).stdout
    name = VERSION_NAME.search(dump)
    code = VERSION_CODE.search(dump)
    return AppInfo(True, name.group(1) if name else None, code.group(1) if code else None)


def launch_app(adb: Adb, serial: str, package: str) -> None:
    adb.shell(serial, "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")


def close_app(adb: Adb, serial: str, package: str) -> None:
    adb.shell(serial, "am", "force-stop", package, check=False)
    adb.shell(serial, "input", "keyevent", "KEYCODE_HOME", check=False)


def time_window(hour: int) -> str:
    """Observation window for a local hour, as defined in docs/research-plan.md."""
    for start, end, name in TIME_WINDOWS:
        if start <= hour < end:
            return name
    return "overnight"
