"""Filesystem layout of the lab and the environment Android tooling runs with."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .config import ConfigError, LabConfig

LAB_HOME_ENV = "NO_ID_LAB_ANDROID_LAB_HOME"
STALE_ANDROID_VARS = ("ANDROID_SDK_HOME",)


@dataclass(frozen=True)
class LabPaths:
    lab_home: Path
    sdk_root: Path
    cmdline_tools_version: str

    @classmethod
    def resolve(cls, config: LabConfig, repo_root: Path, environ: Mapping[str, str]) -> LabPaths:
        lab_home = Path(environ.get(LAB_HOME_ENV) or (repo_root / config.lab_home)).expanduser()
        if not lab_home.is_absolute():
            lab_home = repo_root / lab_home
        if config.sdk_path_policy == "project":
            sdk_root = lab_home / "sdk"
        else:
            sdk_value = environ.get("ANDROID_HOME") or environ.get("ANDROID_SDK_ROOT")
            if not sdk_value:
                raise ConfigError("sdk.path_policy is 'env' but neither ANDROID_HOME nor ANDROID_SDK_ROOT is set")
            sdk_root = Path(sdk_value).expanduser()
        return cls(lab_home=lab_home, sdk_root=sdk_root, cmdline_tools_version=config.cmdline_tools_version)

    @property
    def user_home(self) -> Path:
        return self.lab_home / "user-home"

    @property
    def avd_home(self) -> Path:
        return self.user_home / "avd"

    @property
    def logs_dir(self) -> Path:
        return self.lab_home / "logs"

    @property
    def run_dir(self) -> Path:
        return self.lab_home / "run"

    @property
    def artifacts_dir(self) -> Path:
        return self.lab_home / "artifacts"

    @property
    def cmdline_tools_bin(self) -> Path:
        return self.sdk_root / "cmdline-tools" / self.cmdline_tools_version / "bin"

    @property
    def sdkmanager(self) -> Path:
        return self.cmdline_tools_bin / "sdkmanager"

    @property
    def avdmanager(self) -> Path:
        return self.cmdline_tools_bin / "avdmanager"

    @property
    def adb(self) -> Path:
        return self.sdk_root / "platform-tools" / "adb"

    @property
    def emulator(self) -> Path:
        return self.sdk_root / "emulator" / "emulator"


def build_env(paths: LabPaths, java_home: Path | None, base: Mapping[str, str]) -> dict[str, str]:
    env = {k: v for k, v in base.items() if k not in STALE_ANDROID_VARS}
    prefix = [paths.sdk_root / "platform-tools", paths.sdk_root / "emulator", paths.cmdline_tools_bin]
    if java_home is not None:
        env["JAVA_HOME"] = str(java_home)
        prefix.append(java_home / "bin")
    env.update(
        ANDROID_HOME=str(paths.sdk_root),
        ANDROID_SDK_ROOT=str(paths.sdk_root),
        ANDROID_USER_HOME=str(paths.user_home),
        ANDROID_EMULATOR_HOME=str(paths.user_home),
        ANDROID_AVD_HOME=str(paths.avd_home),
    )
    existing = [p for p in base.get("PATH", "").split(os.pathsep) if p]
    env["PATH"] = os.pathsep.join([*map(str, prefix), *existing])
    return env


def find_java_home(environ: Mapping[str, str], homebrew_jdk: Path | None) -> Path | None:
    """Prefer the Brewfile-pinned JDK; fall back to a JAVA_HOME that actually contains java."""
    candidates = [homebrew_jdk]
    if environ.get("JAVA_HOME"):
        candidates.append(Path(environ["JAVA_HOME"]))
    for candidate in candidates:
        if candidate is not None and (candidate / "bin" / "java").is_file():
            return candidate
    return None


def homebrew_openjdk_home(brew_prefix: Path | None, formula: str = "openjdk@21") -> Path | None:
    if brew_prefix is None:
        return None
    return brew_prefix / "opt" / formula / "libexec" / "openjdk.jdk" / "Contents" / "Home"
