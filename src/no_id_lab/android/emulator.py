"""Emulator process lifecycle: start detached, stop cleanly, report state."""

from __future__ import annotations

import logging
import os
import signal
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from .adb import Adb
from .config import LabConfig
from .paths import LabPaths
from .runner import Runner

log = logging.getLogger(__name__)


class EmulatorError(RuntimeError):
    pass


def build_start_command(config: LabConfig, paths: LabPaths, headless: bool) -> list[str]:
    command = [str(paths.emulator), "-avd", config.avd_name, "-port", str(config.console_port)]
    if headless:
        command += ["-no-window", "-no-audio", "-no-boot-anim", "-gpu", config.headless_gpu]
    else:
        command += ["-gpu", config.gpu]
    if config.boot_mode == "cold":
        command.append("-no-snapshot")
    return command


class Emulator:
    def __init__(
        self,
        config: LabConfig,
        paths: LabPaths,
        runner: Runner,
        adb: Adb,
        env: Mapping[str, str],
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        killpg: Callable[[int, int], None] = os.killpg,
    ) -> None:
        self.config = config
        self.paths = paths
        self.runner = runner
        self.adb = adb
        self.env = env
        self.sleep = sleep
        self.monotonic = monotonic
        self.killpg = killpg

    @property
    def serial(self) -> str:
        return self.config.serial

    @property
    def pid_file(self) -> Path:
        return self.paths.run_dir / f"{self.config.avd_name}.pid"

    @property
    def log_path(self) -> Path:
        return self.paths.logs_dir / f"emulator-{self.config.avd_name}.log"

    def is_running(self) -> bool:
        return self.serial in self.adb.devices()

    def start(self, headless: bool) -> int:
        if self.is_running():
            raise EmulatorError(f"{self.serial} is already running; stop it first")
        command = build_start_command(self.config, self.paths, headless)
        pid = self.runner.spawn(command, env=self.env, log_path=self.log_path)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(pid))
        log.info("Started %s (pid %s, %s); log: %s", self.config.avd_name, pid, "headless" if headless else "windowed", self.log_path)
        return pid

    def stop(self) -> bool:
        """Stop the emulator. Returns False if nothing was running."""
        pid = self._recorded_pid()
        running = self.is_running()
        if not running and not self._pid_alive(pid):
            self.pid_file.unlink(missing_ok=True)
            return False
        if running:
            self.adb.emu_kill(self.serial)
        if not self._wait_until_stopped(pid) and pid is not None and self._pid_alive(pid):
            log.warning("Emulator did not exit after 'emu kill'; sending SIGTERM to process group %s", pid)
            self.killpg(pid, signal.SIGTERM)
            if not self._wait_until_stopped(pid):
                raise EmulatorError(f"{self.serial} (pid {pid}) did not stop within {self.config.stop_timeout_seconds:.0f}s")
        self.pid_file.unlink(missing_ok=True)
        log.info("Stopped %s", self.serial)
        return True

    def log_tail(self, lines: int = 20) -> str:
        if not self.log_path.exists():
            return ""
        return "\n".join(self.log_path.read_text(errors="replace").splitlines()[-lines:])

    def _wait_until_stopped(self, pid: int | None) -> bool:
        started = self.monotonic()
        while True:
            if not self.is_running() and not self._pid_alive(pid):
                return True
            if self.monotonic() - started >= self.config.stop_timeout_seconds:
                return False
            self.sleep(1)

    def _recorded_pid(self) -> int | None:
        try:
            return int(self.pid_file.read_text().strip())
        except (OSError, ValueError):
            return None

    def _pid_alive(self, pid: int | None) -> bool:
        """Only trust the pid file if that pid is still an emulator process."""
        if pid is None:
            return False
        result = self.runner.run(["ps", "-p", str(pid), "-o", "command="], check=False)
        command = result.stdout.strip()
        return "emulator" in command or "qemu-system" in command
