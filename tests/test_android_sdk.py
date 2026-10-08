import os
from pathlib import Path

import pytest

from conftest import LAB_CONFIG
from no_id_lab.android.config import ConfigError, load_config
from no_id_lab.android.paths import LabPaths, build_env, find_java_home
from no_id_lab.android.sdk import SdkManager, ToolNotFoundError, discover_tools, parse_installed_packages

INSTALLED_OUTPUT = """\
Installed packages:
  Path                                        | Version | Description                       | Location
  -------                                     | ------- | -------                           | -------
  cmdline-tools;23.0                          | 23.0    | Android SDK Command-line Tools    | cmdline-tools/23.0
  emulator                                    | 37.2.12 | Android Emulator                  | emulator
  platform-tools                              | 37.0.1  | Android SDK Platform-Tools        | platform-tools
"""


@pytest.fixture
def cfg():
    return load_config(LAB_CONFIG)


def make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path


def make_jdk(root: Path) -> Path:
    make_executable(root / "bin" / "java")
    return root


def test_project_policy_places_sdk_inside_lab_home(cfg, tmp_path):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={"ANDROID_HOME": "/elsewhere"})

    assert paths.lab_home == tmp_path / ".android-lab"
    assert paths.sdk_root == tmp_path / ".android-lab" / "sdk"
    assert paths.user_home == tmp_path / ".android-lab" / "user-home"
    assert paths.avd_home == tmp_path / ".android-lab" / "user-home" / "avd"
    assert paths.logs_dir == tmp_path / ".android-lab" / "logs"
    assert paths.artifacts_dir == tmp_path / ".android-lab" / "artifacts"


def test_lab_home_can_be_overridden_by_environment(cfg, tmp_path):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={"NO_ID_LAB_ANDROID_LAB_HOME": str(tmp_path / "ext")})

    assert paths.lab_home == tmp_path / "ext"
    assert paths.sdk_root == tmp_path / "ext" / "sdk"


def test_env_policy_uses_android_home(cfg, tmp_path):
    cfg = cfg.with_overrides(sdk_path_policy="env")

    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={"ANDROID_HOME": str(tmp_path / "sdk")})

    assert paths.sdk_root == tmp_path / "sdk"


def test_env_policy_falls_back_to_android_sdk_root(cfg, tmp_path):
    cfg = cfg.with_overrides(sdk_path_policy="env")

    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={"ANDROID_SDK_ROOT": str(tmp_path / "legacy")})

    assert paths.sdk_root == tmp_path / "legacy"


def test_env_policy_without_android_home_is_an_error(cfg, tmp_path):
    cfg = cfg.with_overrides(sdk_path_policy="env")

    with pytest.raises(ConfigError, match="ANDROID_HOME"):
        LabPaths.resolve(cfg, repo_root=tmp_path, environ={})


def test_tool_paths_follow_sdk_layout(cfg, tmp_path):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    sdk = paths.sdk_root

    assert paths.sdkmanager == sdk / "cmdline-tools" / "23.0" / "bin" / "sdkmanager"
    assert paths.avdmanager == sdk / "cmdline-tools" / "23.0" / "bin" / "avdmanager"
    assert paths.adb == sdk / "platform-tools" / "adb"
    assert paths.emulator == sdk / "emulator" / "emulator"


def test_build_env_points_android_tooling_at_lab_paths(cfg, tmp_path):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    java_home = tmp_path / "jdk"

    env = build_env(paths, java_home, {"PATH": "/usr/bin", "ANDROID_SDK_HOME": "/stale"})

    assert env["ANDROID_HOME"] == str(paths.sdk_root)
    assert env["ANDROID_SDK_ROOT"] == str(paths.sdk_root)
    assert env["ANDROID_USER_HOME"] == str(paths.user_home)
    assert env["ANDROID_EMULATOR_HOME"] == str(paths.user_home)
    assert env["ANDROID_AVD_HOME"] == str(paths.avd_home)
    assert env["JAVA_HOME"] == str(java_home)
    assert "ANDROID_SDK_HOME" not in env
    path_entries = env["PATH"].split(os.pathsep)
    assert path_entries[:4] == [
        str(paths.sdk_root / "platform-tools"),
        str(paths.sdk_root / "emulator"),
        str(paths.sdkmanager.parent),
        str(java_home / "bin"),
    ]
    assert path_entries[-1] == "/usr/bin"


def test_find_java_home_prefers_homebrew_openjdk(tmp_path):
    brew_jdk = make_jdk(tmp_path / "brew-jdk")
    env_jdk = make_jdk(tmp_path / "env-jdk")

    assert find_java_home({"JAVA_HOME": str(env_jdk)}, brew_jdk) == brew_jdk


def test_find_java_home_ignores_stale_java_home(tmp_path):
    assert find_java_home({"JAVA_HOME": "/usr/lib/jvm/java-8-openjdk/jre/"}, None) is None


def test_find_java_home_uses_valid_java_home_without_homebrew(tmp_path):
    env_jdk = make_jdk(tmp_path / "env-jdk")

    assert find_java_home({"JAVA_HOME": str(env_jdk)}, tmp_path / "missing") == env_jdk


def test_discover_tools_reports_present_and_missing(cfg, tmp_path):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    make_executable(paths.adb)
    make_executable(paths.emulator)

    tools = discover_tools(paths, java_home=None)

    assert tools["adb"] == paths.adb
    assert tools["emulator"] == paths.emulator
    assert tools["sdkmanager"] is None
    assert tools["avdmanager"] is None
    assert tools["java"] is None


ANDROID_CLI_INSTALLED_OUTPUT = """\
Installed packages:
  cmdline-tools/23.0                                     23.0.0      Android SDK Command-line Tools
  emulator                                               37.2.12     Android Emulator
  platform-tools                                         37.0.1      Android SDK Platform-Tools
  system-images/android-35/google_apis/arm64-v8a         9.0.0       Google APIs ARM 64 v8a System Image
"""


def test_parse_installed_packages():
    assert parse_installed_packages(INSTALLED_OUTPUT) == {"cmdline-tools;23.0", "emulator", "platform-tools"}


def test_parse_installed_packages_from_android_cli_format():
    assert parse_installed_packages(ANDROID_CLI_INSTALLED_OUTPUT) == {
        "cmdline-tools;23.0",
        "emulator",
        "platform-tools",
        "system-images;android-35;google_apis;arm64-v8a",
    }


def test_bootstrap_sdkmanager_prefers_project_copy(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    make_executable(paths.sdkmanager)

    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/opt/homebrew/bin/sdkmanager")

    assert sdk.sdkmanager() == paths.sdkmanager


def test_bootstrap_sdkmanager_falls_back_to_path(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})

    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/opt/homebrew/bin/sdkmanager")

    assert sdk.sdkmanager() == Path("/opt/homebrew/bin/sdkmanager")


def test_bootstrap_sdkmanager_missing_explains_how_to_install(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    sdk = SdkManager(paths, runner, env={}, which=lambda name: None)

    with pytest.raises(ToolNotFoundError, match="brew bundle"):
        sdk.sdkmanager()


def test_accept_licenses_answers_yes_noninteractively(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    sdk = SdkManager(paths, runner, env={"X": "1"}, which=lambda name: "/bin/sdkmanager")

    sdk.accept_licenses()

    call = runner.calls[-1]
    assert call["args"] == ("/bin/sdkmanager", f"--sdk_root={paths.sdk_root}", "--licenses")
    assert call["input"].startswith("y\ny\n")
    assert call["env"] == {"X": "1"}


def test_ensure_packages_installs_only_missing(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    runner.on("--list_installed", INSTALLED_OUTPUT)
    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/bin/sdkmanager")
    wanted = cfg.required_packages("arm64")

    installed = sdk.ensure_packages(wanted)

    assert installed == ["system-images;android-35;google_apis;arm64-v8a"]
    install_calls = [line for line in runner.lines() if "--install" in line]
    assert install_calls == [
        f"/bin/sdkmanager --sdk_root={paths.sdk_root} --install system-images;android-35;google_apis;arm64-v8a"
    ]


def test_ensure_packages_is_noop_when_everything_installed(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    runner.on("--list_installed", INSTALLED_OUTPUT)
    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/bin/sdkmanager")

    assert sdk.ensure_packages(["platform-tools", "emulator"]) == []
    assert not any("--install" in line for line in runner.lines())
