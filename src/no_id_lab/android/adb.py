"""Thin adb wrapper shared by lifecycle, boot detection, and future evidence capture."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from .runner import CommandError, CommandResult, Runner

ADB_TIMEOUT_SECONDS = 60


def parse_adb_devices(output: str) -> dict[str, str]:
    devices = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.startswith(("List of devices", "*")):
            devices[parts[0]] = parts[1]
    return devices


class Adb:
    def __init__(self, path: Path, runner: Runner, env: Mapping[str, str]) -> None:
        self.path = path
        self.runner = runner
        self.env = env

    def run(self, *args: str, check: bool = True, timeout: float = ADB_TIMEOUT_SECONDS) -> CommandResult:
        return self.runner.run([self.path, *args], env=self.env, timeout=timeout, check=check)

    def devices(self) -> dict[str, str]:
        return parse_adb_devices(self.run("devices").stdout)

    def shell(self, serial: str, *command: str, check: bool = True) -> CommandResult:
        return self.run("-s", serial, "shell", *command, check=check)

    def getprop(self, serial: str, name: str) -> str:
        try:
            return self.shell(serial, "getprop", name, check=False).stdout.strip()
        except CommandError:
            return ""

    def emu_kill(self, serial: str) -> None:
        self.run("-s", serial, "emu", "kill", check=False)

    def screenshot(self, serial: str, dest: Path) -> Path:
        remote = "/data/local/tmp/no-id-lab-screenshot.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.shell(serial, "screencap", "-p", remote)
        self.run("-s", serial, "pull", remote, str(dest))
        self.shell(serial, "rm", "-f", remote, check=False)
        return dest
