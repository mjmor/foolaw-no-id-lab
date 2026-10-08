from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT
from no_id_lab.android.adb import Adb
from no_id_lab.android.apps import AppSpec, app_info, close_app, launch_app, load_apps_config, time_window
from no_id_lab.android.config import ConfigError

APPS_CONFIG = REPO_ROOT / "configs" / "android" / "apps.yaml"
SERIAL = "emulator-5554"


def write_apps(tmp_path: Path, apps) -> Path:
    data = yaml.safe_load(APPS_CONFIG.read_text())
    data["apps"] = apps
    path = tmp_path / "apps.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def test_apps_config_covers_every_in_scope_app():
    config = load_apps_config(APPS_CONFIG)

    assert {app.name for app in config.apps} >= {"YouTube", "Instagram", "Facebook", "Snapchat", "TikTok", "Kick"}
    assert {app.package for app in config.apps} >= {
        "com.google.android.youtube",
        "com.instagram.android",
        "com.facebook.katana",
        "com.snapchat.android",
        "com.zhiliaoapp.musically",
        "com.kick.mobile",
    }
    assert config.record_seconds > 0
    assert config.record_fps == 24
    assert config.install_timeout_seconds > 0
    assert config.captures_dir == "captures"


def test_select_returns_requested_apps_in_config_order():
    config = load_apps_config(APPS_CONFIG)

    assert [app.id for app in config.select(["tiktok", "youtube"])] == ["youtube", "tiktok"]
    assert config.select(None) == list(config.apps)


def test_select_rejects_unknown_app_ids():
    with pytest.raises(ConfigError, match="unknown app id"):
        load_apps_config(APPS_CONFIG).select(["myspace"])


@pytest.mark.parametrize(
    ("apps", "message"),
    [
        ([{"id": "a", "name": "A", "package": "com.a"}, {"id": "a", "name": "B", "package": "com.b"}], "duplicate"),
        ([{"id": "a", "name": "A", "package": "not a package"}], "package"),
        ([{"id": "a", "name": "A"}], "package"),
        ([], "at least one app"),
    ],
)
def test_invalid_apps_config_is_rejected(tmp_path, apps, message):
    with pytest.raises(ConfigError, match=message):
        load_apps_config(write_apps(tmp_path, apps))


@pytest.mark.parametrize(
    ("hour", "window"),
    [(6, "morning"), (8, "morning"), (9, "school_hours"), (14, "school_hours"), (15, "after_school"),
     (18, "evening"), (21, "evening"), (22, "overnight"), (0, "overnight"), (5, "overnight")],
)
def test_time_window_follows_research_plan(hour, window):
    assert time_window(hour) == window


@pytest.fixture
def adb(runner):
    return Adb(Path("/sdk/platform-tools/adb"), runner, env={})


def test_app_info_reports_installed_version(adb, runner):
    runner.on("pm path com.google.android.youtube", "package:/product/app/YouTube/YouTube.apk\n")
    runner.on("dumpsys package com.google.android.youtube", "    versionCode=1545868760 minSdk=26\n    versionName=19.17.42\n")

    info = app_info(adb, SERIAL, "com.google.android.youtube")

    assert info.installed is True
    assert info.version_name == "19.17.42"
    assert info.version_code == "1545868760"


def test_app_info_reports_missing_app(adb, runner):
    runner.on("pm path com.kick.mobile", "", returncode=1)

    info = app_info(adb, SERIAL, "com.kick.mobile")

    assert info.installed is False
    assert info.version_name is None


def test_launch_and_close_use_launcher_intent_and_force_stop(adb, runner):
    app = AppSpec(id="kick", name="Kick", package="com.kick.mobile")

    launch_app(adb, SERIAL, app.package)
    close_app(adb, SERIAL, app.package)

    lines = runner.lines()
    assert "/sdk/platform-tools/adb -s emulator-5554 shell monkey -p com.kick.mobile -c android.intent.category.LAUNCHER 1" in lines
    assert "/sdk/platform-tools/adb -s emulator-5554 shell am force-stop com.kick.mobile" in lines
    assert "/sdk/platform-tools/adb -s emulator-5554 shell input keyevent KEYCODE_HOME" in lines
