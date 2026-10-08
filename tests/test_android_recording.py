import hashlib
import json
from pathlib import Path

import pytest

from conftest import LAB_CONFIG, REPO_ROOT
from no_id_lab.android.adb import Adb
from no_id_lab.android.apps import AppSpec, load_apps_config
from no_id_lab.android.config import load_config
from no_id_lab.android.recording import AppRecorder
from no_id_lab.android.runner import CommandError, CommandResult

SERIAL = "emulator-5554"
YOUTUBE = AppSpec(id="youtube", name="YouTube", package="com.google.android.youtube")
KICK = AppSpec(id="kick", name="Kick", package="com.kick.mobile")
VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42"


@pytest.fixture
def recorder(runner, tmp_path):
    def pull(args):
        Path(args[-1]).write_bytes(VIDEO_BYTES)

    runner.hook(" pull ", pull)
    runner.on("pm path com.google.android.youtube", "package:/product/app/YouTube/YouTube.apk\n")
    runner.on("dumpsys package com.google.android.youtube", "    versionCode=1545868760\n    versionName=19.17.42\n")
    runner.on("pm path com.kick.mobile", "")
    runner.on("pidof screenrecord", "4321\n")
    runner.on("date +%Y-%m-%dT%H:%M:%S%z", "2026-10-07T19:05:00-0400\n")
    runner.on("getprop ro.build.version.release", "15\n")
    return AppRecorder(
        Adb(Path("/adb"), runner, env={}),
        SERIAL,
        load_apps_config(REPO_ROOT / "configs" / "android" / "apps.yaml"),
        load_config(LAB_CONFIG),
        output_dir=tmp_path / "run",
        machine="arm64",
        sleep=lambda seconds: None,
    )


def test_record_captures_launch_with_screenrecord_and_writes_manifest(recorder, runner, tmp_path):
    result = recorder.record(YOUTUBE)

    assert result.status == "recorded"
    assert result.video == tmp_path / "run" / "youtube.mp4"
    lines = runner.lines()
    assert (
        "/adb -s emulator-5554 shell screenrecord --time-limit 20 --bit-rate 4M --bugreport "
        "/data/local/tmp/no-id-lab-youtube.mp4"
    ) in lines
    assert "/adb -s emulator-5554 shell monkey -p com.google.android.youtube -c android.intent.category.LAUNCHER 1" in lines
    assert f"/adb -s emulator-5554 pull /data/local/tmp/no-id-lab-youtube.mp4 {tmp_path / 'run' / 'youtube.mp4'}" in lines
    assert "/adb -s emulator-5554 shell rm -f /data/local/tmp/no-id-lab-youtube.mp4" in lines
    assert lines.count("/adb -s emulator-5554 shell am force-stop com.google.android.youtube") == 2

    manifest = json.loads(result.manifest.read_text())
    assert manifest["platform"] == "android_emulator"
    assert manifest["app"] == "YouTube"
    assert manifest["package"] == "com.google.android.youtube"
    assert manifest["app_version"] == "19.17.42"
    assert manifest["os_version"] == "Android 15"
    assert manifest["local_time"] == "2026-10-07T19:05:00-0400"
    assert manifest["time_window"] == "evening"
    assert manifest["evidence_artifact"] == "youtube.mp4"
    assert manifest["sha256"] == hashlib.sha256(VIDEO_BYTES).hexdigest()
    assert manifest["persona"] is None
    assert manifest["statute_hook"] is None
    assert manifest["device"]["avd_name"] == "no-id-lab-api35-play"
    assert manifest["recording"]["seconds"] == 20


def test_record_skips_apps_that_are_not_installed(recorder, runner):
    result = recorder.record(KICK)

    assert result.status == "skipped-not-installed"
    assert not any("screenrecord" in line for line in runner.lines())


def test_record_reports_failed_recording_and_still_closes_app(recorder, runner):
    failure = CommandError(CommandResult(("screenrecord",), 1, "", "Unable to get output buffers"))
    runner.on("shell screenrecord", failure)

    result = recorder.record(YOUTUBE)

    assert result.status == "failed"
    assert "Unable to get output buffers" in result.detail
    assert runner.lines()[-1] == "/adb -s emulator-5554 shell input keyevent KEYCODE_HOME"


def test_record_all_writes_run_summary(recorder, tmp_path):
    results = recorder.record_all([YOUTUBE, KICK])

    assert [r.status for r in results] == ["recorded", "skipped-not-installed"]
    summary = json.loads((tmp_path / "run" / "run.json").read_text())
    assert [entry["status"] for entry in summary["results"]] == ["recorded", "skipped-not-installed"]
    assert summary["results"][0]["manifest"] == "youtube.json"
