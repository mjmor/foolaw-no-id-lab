"""AVD creation, convergence, and validation against the declarative config."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from .config import LabConfig
from .paths import LabPaths
from .runner import Runner

log = logging.getLogger(__name__)

EnsureResult = Literal["created", "recreated", "updated", "unchanged"]


def read_ini(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def write_ini(path: Path, updates: Mapping[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(updates)
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key is not None and key in pending:
            out.append(f"{key}={pending.pop(key)}")
        elif key is not None:
            out.append(f"{key}={line.split('=', 1)[1].strip()}")
        else:
            out.append(line)
    out.extend(f"{k}={v}" for k, v in pending.items())
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


class AvdManager:
    def __init__(
        self,
        config: LabConfig,
        paths: LabPaths,
        runner: Runner,
        env: Mapping[str, str],
        machine: str | None = None,
    ) -> None:
        self.config = config
        self.paths = paths
        self.runner = runner
        self.env = env
        self.machine = machine

    @property
    def name(self) -> str:
        return self.config.avd_name

    @property
    def ini_path(self) -> Path:
        return self.paths.avd_home / f"{self.name}.ini"

    @property
    def config_path(self) -> Path:
        return self.paths.avd_home / f"{self.name}.avd" / "config.ini"

    def exists(self) -> bool:
        return self.ini_path.is_file() and self.config_path.is_file()

    def expected_identity(self) -> dict[str, str]:
        return {
            "image.sysdir.1": self.config.system_image_dir(self.machine),
            "hw.device.name": self.config.device_profile,
            "abi.type": self.config.abi(self.machine),
            "tag.id": self.config.image_tag,
        }

    def create(self) -> None:
        self.paths.avd_home.mkdir(parents=True, exist_ok=True)
        self.runner.run(
            [
                self.paths.avdmanager,
                "create",
                "avd",
                "--name",
                self.name,
                "--package",
                self.config.system_image_package(self.machine),
                "--device",
                self.config.device_profile,
                "--sdcard",
                self.config.sdcard_size,
                "--force",
            ],
            env=self.env,
            input="no\n",
            timeout=600,
        )

    def ensure(self) -> EnsureResult:
        if not self.exists():
            log.info("Creating AVD %s", self.name)
            self.create()
            self._apply_hardware()
            return "created"
        if self._identity_drift():
            log.info("Recreating AVD %s to match the configured system image and device", self.name)
            self.create()
            self._apply_hardware()
            return "recreated"
        if self._hardware_drift():
            self._apply_hardware()
            return "updated"
        return "unchanged"

    def validate(self) -> list[str]:
        if not self.exists():
            return [f"AVD '{self.name}' does not exist in {self.paths.avd_home}"]
        return self._identity_drift() + self._hardware_drift()

    def _apply_hardware(self) -> None:
        write_ini(self.config_path, self.config.hardware)

    def _identity_drift(self) -> list[str]:
        return _drift(read_ini(self.config_path), self.expected_identity())

    def _hardware_drift(self) -> list[str]:
        return _drift(read_ini(self.config_path), self.config.hardware)


def _drift(actual: Mapping[str, str], expected: Mapping[str, str]) -> list[str]:
    return [
        f"{key} is {actual.get(key)!r}, expected {value!r}"
        for key, value in expected.items()
        if actual.get(key) != value
    ]
