"""Android SDK discovery and package installation via the `android` CLI (`android sdk ...`)."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from .paths import LabPaths
from .runner import CommandResult, Runner

log = logging.getLogger(__name__)

INSTALL_TIMEOUT_SECONDS = 3600


class ToolNotFoundError(RuntimeError):
    pass


def discover_tools(paths: LabPaths, java_home: Path | None) -> dict[str, Path | None]:
    tools = {
        "java": java_home / "bin" / "java" if java_home else None,
        "android": paths.android_cli,
        "avdmanager": paths.avdmanager,
        "adb": paths.adb,
        "emulator": paths.emulator,
    }
    return {name: path if path is not None and _is_executable(path) else None for name, path in tools.items()}


def package_path(package: str) -> str:
    """Normalise `a;b;c` package ids to the CLI's `a/b/c` form."""
    return package.replace(";", "/")


def parse_installed_packages(output: str) -> set[str]:
    """Parse `android sdk list`: an `Installed packages:` header, then indented `path  version  description` rows."""
    packages = set()
    for line in output.splitlines():
        if line[:1].isspace() and line.strip():
            packages.add(package_path(line.split()[0]))
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

    def android_cli(self) -> Path:
        """The SDK's own pinned `android` CLI, or the Homebrew bootstrap copy before it is installed."""
        if _is_executable(self.paths.android_cli):
            return self.paths.android_cli
        found = self.which("android")
        if found:
            return Path(found)
        raise ToolNotFoundError(
            "The `android` CLI was not found. Install the Android command-line tools with "
            "`brew bundle --file=Brewfile` (or run scripts/setup_macos.sh)."
        )

    def _run(self, *args: str, timeout: float | None = None) -> CommandResult:
        return self.runner.run(
            [self.android_cli(), "--no-metrics", f"--sdk={self.paths.sdk_root}", *args],
            env=self.env,
            input="",
            timeout=timeout,
        )

    def installed_packages(self) -> set[str]:
        return parse_installed_packages(self._run("sdk", "list", timeout=600).stdout)

    def ensure_packages(self, packages: Iterable[str]) -> list[str]:
        self.paths.sdk_root.mkdir(parents=True, exist_ok=True)
        installed = self.installed_packages()
        missing = [package_path(p) for p in packages if package_path(p) not in installed]
        for package in missing:
            log.info("Installing SDK package %s", package)
            self._run("sdk", "install", package, timeout=INSTALL_TIMEOUT_SECONDS)
        return missing


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)
