import os
from pathlib import Path

import pytest

from conftest import LAB_CONFIG
from no_id_lab.android.config import ConfigError, load_config
from no_id_lab.android.paths import LabPaths, build_env, find_java_home
from no_id_lab.android.sdk import (
    SdkManager,
    ToolNotFoundError,
    discover_tools,
    package_path,
    parse_installed_packages,
)


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

    assert paths.android_cli == sdk / "cmdline-tools" / "23.0" / "bin" / "android"
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
        str(paths.android_cli.parent),
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
    assert tools["android"] is None
    assert tools["avdmanager"] is None
    assert tools["java"] is None


ANDROID_CLI_INSTALLED_OUTPUT = """\
Installed packages:
  cmdline-tools/23.0                                     23.0.0      Android SDK Command-line Tools
  emulator                                               37.2.12     Android Emulator
  platform-tools                                         37.0.1      Android SDK Platform-Tools
"""


def test_parse_installed_packages_from_android_cli_listing():
    output = ANDROID_CLI_INSTALLED_OUTPUT + (
        "  system-images/android-35/google_apis_playstore/arm64-v8a   9.0.0   Google Play ARM 64 v8a System Image\n"
    )

    assert parse_installed_packages(output) == {
        "cmdline-tools/23.0",
        "emulator",
        "platform-tools",
        "system-images/android-35/google_apis_playstore/arm64-v8a",
    }


def test_package_paths_are_normalised_to_android_cli_form():
    assert package_path("system-images;android-35;google_apis_playstore;arm64-v8a") == (
        "system-images/android-35/google_apis_playstore/arm64-v8a"
    )
    assert package_path("platform-tools") == "platform-tools"


def test_android_cli_prefers_project_copy(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    make_executable(paths.android_cli)

    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/opt/homebrew/bin/android")

    assert sdk.android_cli() == paths.android_cli


def test_android_cli_falls_back_to_homebrew_bootstrap_on_path(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    looked_up = []

    sdk = SdkManager(paths, runner, env={}, which=lambda name: looked_up.append(name) or "/opt/homebrew/bin/android")

    assert sdk.android_cli() == Path("/opt/homebrew/bin/android")
    assert looked_up == ["android"]


def test_android_cli_missing_explains_how_to_install(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    sdk = SdkManager(paths, runner, env={}, which=lambda name: None)

    with pytest.raises(ToolNotFoundError, match="brew bundle"):
        sdk.android_cli()


def test_android_cli_calls_disable_metrics_and_pin_sdk_root(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    runner.on("sdk list", ANDROID_CLI_INSTALLED_OUTPUT)
    sdk = SdkManager(paths, runner, env={"X": "1"}, which=lambda name: "/bin/android")

    sdk.installed_packages()

    call = runner.calls[-1]
    assert call["args"] == ("/bin/android", "--no-metrics", f"--sdk={paths.sdk_root}", "sdk", "list")
    assert call["env"] == {"X": "1"}


def test_ensure_packages_installs_only_missing_with_closed_stdin(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    runner.on("sdk list", ANDROID_CLI_INSTALLED_OUTPUT)
    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/bin/android")
    wanted = cfg.required_packages("arm64")

    installed = sdk.ensure_packages(wanted)

    assert installed == ["system-images/android-35/google_apis_playstore/arm64-v8a"]
    install_calls = [call for call in runner.calls if "install" in call["args"]]
    assert [call["args"] for call in install_calls] == [
        (
            "/bin/android",
            "--no-metrics",
            f"--sdk={paths.sdk_root}",
            "sdk",
            "install",
            "system-images/android-35/google_apis_playstore/arm64-v8a",
        )
    ]
    assert install_calls[0]["input"] == ""


def test_ensure_packages_accepts_semicolon_package_ids(cfg, tmp_path, runner):
    paths = LabPaths.resolve(cfg, repo_root=tmp_path, environ={})
    runner.on("sdk list", ANDROID_CLI_INSTALLED_OUTPUT)
    sdk = SdkManager(paths, runner, env={}, which=lambda name: "/bin/android")

    assert sdk.ensure_packages(["cmdline-tools;23.0", "platform-tools", "emulator"]) == []
    assert not any("install" in call["args"] for call in runner.calls)
