"""Android SDK discovery and package installation via sdkmanager."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from .paths import LabPaths
from .runner import Runner

log = logging.getLogger(__name__)

INSTALL_TIMEOUT_SECONDS = 3600
LICENSE_ANSWERS = "y\n" * 100


class ToolNotFoundError(RuntimeError):
    pass


def discover_tools(paths: LabPaths, java_home: Path | None) -> dict[str, Path | None]:
    tools = {
        "java": java_home / "bin" / "java" if java_home else None,
        "sdkmanager": paths.sdkmanager,
        "avdmanager": paths.avdmanager,
        "adb": paths.adb,
        "emulator": paths.emulator,
    }
    return {name: path if path is not None and _is_executable(path) else None for name, path in tools.items()}


def parse_installed_packages(output: str) -> set[str]:
    """Parse both the classic `|` table and the Android CLI's `a/b/c  version  description` listing."""
    packages = set()
    for line in output.splitlines():
        if not line[:1].isspace() or not line.strip():
            continue
        name = line.split("|", 1)[0].strip() if "|" in line else line.split()[0]
        if name and name != "Path" and not name.startswith("-"):
            packages.add(name.replace("/", ";"))
    return packages


class SdkManager:
    def __init__(
        self,
        paths: LabPaths,
        runner: Runner,
        env: Mapping[str, str],
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.paths = paths
        self.runner = runner
        self.env = env
        self.which = which

    def sdkmanager(self) -> Path:
        """The SDK's own pinned sdkmanager, or the Homebrew bootstrap copy before it is installed."""
        if _is_executable(self.paths.sdkmanager):
            return self.paths.sdkmanager
        found = self.which("sdkmanager")
        if found:
            return Path(found)
        raise ToolNotFoundError(
            "sdkmanager not found. Install the Android command-line tools with "
            "`brew bundle --file=Brewfile` (or run scripts/setup_macos.sh)."
        )

    def _run(self, *args: str, input: str | None = None, timeout: float | None = None):
        return self.runner.run(
            [self.sdkmanager(), f"--sdk_root={self.paths.sdk_root}", *args],
            env=self.env,
            input=input,
            timeout=timeout,
        )

    def accept_licenses(self) -> None:
        self._run("--licenses", input=LICENSE_ANSWERS, timeout=600)

    def installed_packages(self) -> set[str]:
        return parse_installed_packages(self._run("--list_installed", timeout=600).stdout)

    def ensure_packages(self, packages: Iterable[str]) -> list[str]:
        self.paths.sdk_root.mkdir(parents=True, exist_ok=True)
        installed = self.installed_packages()
        missing = [p for p in packages if p not in installed]
        for package in missing:
            log.info("Installing SDK package %s", package)
            self._run("--install", package, input=LICENSE_ANSWERS, timeout=INSTALL_TIMEOUT_SECONDS)
        return missing


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)
