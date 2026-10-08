"""AndroidLab composes SDK, AVD, adb, and emulator lifecycle into lab-level operations."""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .adb import Adb
from .avd import AvdManager
from .boot import BootTimeoutError, is_booted, wait_for_boot
from .config import LabConfig
from .emulator import Emulator, EmulatorError
from .paths import LabPaths, build_env, find_java_home, homebrew_openjdk_home
from .runner import Runner, SubprocessRunner
from .sdk import SdkManager, ToolNotFoundError, discover_tools

log = logging.getLogger(__name__)

CONFIG_RELATIVE_PATH = Path("configs") / "android" / "lab.yaml"
VALIDATION_PROPERTIES = (
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.product.model",
    "ro.product.cpu.abi",
    "ro.kernel.qemu",
    "sys.boot_completed",
)


def find_repo_root(start: Path | None = None) -> Path:
    for candidate in [Path(start or Path.cwd()).resolve(), *Path(start or Path.cwd()).resolve().parents]:
        if (candidate / CONFIG_RELATIVE_PATH).is_file():
            return candidate
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ValidationReport:
    serial: str
    avd_name: str
    properties: dict[str, str]
    screenshot: Path
    output_dir: Path
    boot_seconds: float


class AndroidLab:
    def __init__(
        self,
        config: LabConfig,
        paths: LabPaths,
        runner: Runner,
        env: Mapping[str, str],
        java_home: Path | None,
        machine: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.config = config
        self.paths = paths
        self.runner = runner
        self.env = dict(env)
        self.java_home = java_home
        self.machine = machine or platform.machine()
        self.sleep = sleep
        self.monotonic = monotonic
        self.sdk = SdkManager(paths, runner, self.env, which=which)
        self.avd = AvdManager(config, paths, runner, self.env, machine=self.machine)
        self.adb = Adb(paths.adb, runner, self.env)
        self.emulator = Emulator(config, paths, runner, self.adb, self.env, sleep=sleep, monotonic=monotonic)

    @classmethod
    def from_environment(
        cls,
        config: LabConfig,
        repo_root: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> AndroidLab:
        environ = os.environ if environ is None else environ
        runner = SubprocessRunner()
        paths = LabPaths.resolve(config, repo_root or find_repo_root(), environ)
        java_home = find_java_home(environ, homebrew_openjdk_home(_brew_prefix(runner)))
        return cls(config, paths, runner, build_env(paths, java_home, environ), java_home)

    def tools(self) -> dict[str, Path | None]:
        return discover_tools(self.paths, self.java_home)

    def setup(self) -> dict[str, object]:
        """Converge SDK packages and the AVD to the config. Safe to rerun."""
        if self.java_home is None:
            raise ToolNotFoundError("No Java runtime found. Run `brew bundle --file=Brewfile` to install openjdk@21.")
        self.paths.sdk_root.mkdir(parents=True, exist_ok=True)
        self.paths.avd_home.mkdir(parents=True, exist_ok=True)
        installed = self.sdk.ensure_packages(self.config.required_packages(self.machine))
        avd_state = self.avd.ensure()
        return {"installed_packages": installed, "avd": avd_state}

    def start(self, headless: bool | None = None, wait: bool = True) -> bool:
        """Start the emulator and wait for boot. Returns False if it was already running."""
        headless = self.config.headless if headless is None else headless
        if self.emulator.is_running():
            log.info("%s is already running", self.emulator.serial)
            if wait:
                self.wait_for_boot()
            return False
        problems = self.avd.validate()
        if not self.avd.exists():
            raise EmulatorError(f"{problems[0]}. Run scripts/setup_macos.sh first.")
        for problem in problems:
            log.warning("AVD drift: %s (rerun scripts/setup_macos.sh to converge)", problem)
        for attempt in range(1, self.config.boot_attempts + 1):
            self.emulator.start(headless=headless)
            if not wait:
                return True
            try:
                self.wait_for_boot()
                return True
            except BootTimeoutError as exc:
                log.warning("Boot attempt %d/%d failed: %s", attempt, self.config.boot_attempts, exc)
                self.emulator.stop()
                if attempt == self.config.boot_attempts:
                    raise EmulatorError(f"{exc}\nLast emulator log lines:\n{self.emulator.log_tail()}") from exc
        return True

    def wait_for_boot(self, timeout: float | None = None) -> float:
        return wait_for_boot(
            self.adb,
            self.emulator.serial,
            timeout=timeout or self.config.boot_timeout_seconds,
            poll_interval=self.config.poll_interval_seconds,
            sleep=self.sleep,
            monotonic=self.monotonic,
        )

    def stop(self) -> bool:
        return self.emulator.stop()

    def status(self) -> dict[str, object]:
        devices = self.adb.devices()
        return {
            "avd": self.config.avd_name,
            "serial": self.emulator.serial,
            "adb_state": devices.get(self.emulator.serial, "absent"),
            "booted": is_booted(self.adb, self.emulator.serial) if self.emulator.serial in devices else False,
        }

    def validate(self, headless: bool | None = None, keep_running: bool = False) -> ValidationReport:
        """Start (if needed), confirm adb reachability, record properties and a screenshot, then stop."""
        started_at = self.monotonic()
        spawned = self.start(headless=headless, wait=True)
        try:
            serial = self.emulator.serial
            state = self.adb.devices().get(serial)
            if state != "device":
                raise EmulatorError(f"adb reports {serial} as {state or 'absent'}, expected 'device'")
            properties = {name: self.adb.getprop(serial, name) for name in VALIDATION_PROPERTIES}
            if properties["ro.build.version.sdk"] != str(self.config.api_level):
                raise EmulatorError(
                    f"Emulator API level is {properties['ro.build.version.sdk']!r}, expected {self.config.api_level}"
                )
            expected_abi = self.config.abi(self.machine)
            if properties["ro.product.cpu.abi"] != expected_abi:
                raise EmulatorError(f"Emulator ABI is {properties['ro.product.cpu.abi']!r}, expected {expected_abi!r}")
            output_dir = self.paths.artifacts_dir / "validation" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            output_dir.mkdir(parents=True, exist_ok=True)
            screenshot = self.adb.screenshot(serial, output_dir / "screenshot.png")
            report = ValidationReport(
                serial=serial,
                avd_name=self.config.avd_name,
                properties=properties,
                screenshot=screenshot,
                output_dir=output_dir,
                boot_seconds=self.monotonic() - started_at,
            )
            (output_dir / "device-properties.json").write_text(
                json.dumps(
                    {
                        "captured_at": datetime.now(UTC).isoformat(),
                        "serial": serial,
                        "avd_name": self.config.avd_name,
                        "api_level": self.config.api_level,
                        "system_image": self.config.system_image_package(self.machine),
                        "properties": properties,
                    },
                    indent=2,
                )
                + "\n"
            )
            return report
        finally:
            if spawned and not keep_running:
                self.emulator.stop()


def _brew_prefix(runner: Runner) -> Path | None:
    brew = shutil.which("brew")
    if brew is None:
        return None
    result = runner.run([brew, "--prefix"], check=False, timeout=30)
    return Path(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None
