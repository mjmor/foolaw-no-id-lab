import hashlib
import json
from pathlib import Path

import pytest

from conftest import LAB_CONFIG, REPO_ROOT
from no_id_lab.android.adb import Adb
from no_id_lab.android.apps import AppSpec, load_apps_config
from no_id_lab.android.config import load_config
from no_id_lab.android.recording import AppRecorder
from no_id_lab.android.runner import CommandResult

SERIAL = "emulator-5554"
YOUTUBE = AppSpec(id="youtube", name="YouTube", package="com.google.android.youtube")
KICK = AppSpec(id="kick", name="Kick", package="com.kick.mobile")
VIDEO_BYTES = b"\x1a\x45\xdf\xa3webm"


@pytest.fixture
def recorder(runner, tmp_path):
    def emulator_writes_video(args):
        Path(args[-1]).write_bytes(VIDEO_BYTES)

    runner.hook("emu screenrecord start", emulator_writes_video)
    runner.on("emu screenrecord", "OK\n")
    runner.on("pm path com.google.android.youtube", "package:/product/app/YouTube/YouTube.apk\n")
    runner.on("dumpsys package com.google.android.youtube", "    versionCode=1545868760\n    versionName=19.17.42\n")
    runner.on("pm path com.kick.mobile", "")
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


def test_record_captures_launch_with_emulator_recorder_and_writes_manifest(recorder, runner, tmp_path):
    result = recorder.record(YOUTUBE)

    assert result.status == "recorded"
    video = tmp_path / "run" / "youtube.webm"
    assert result.video == video
    lines = runner.lines()
    start = f"/adb -s emulator-5554 emu screenrecord start --time-limit 21 --bit-rate 4M --fps 24 {video}"
    launch = "/adb -s emulator-5554 shell monkey -p com.google.android.youtube -c android.intent.category.LAUNCHER 1"
    stop = "/adb -s emulator-5554 emu screenrecord stop"
    assert lines.index(start) < lines.index(launch) < lines.index(stop)
    assert lines.count("/adb -s emulator-5554 shell am force-stop com.google.android.youtube") == 2

    manifest = json.loads(result.manifest.read_text())
    assert manifest["platform"] == "android_emulator"
    assert manifest["app"] == "YouTube"
    assert manifest["package"] == "com.google.android.youtube"
    assert manifest["app_version"] == "19.17.42"
    assert manifest["os_version"] == "Android 15"
    assert manifest["local_time"] == "2026-10-07T19:05:00-0400"
    assert manifest["time_window"] == "evening"
    assert manifest["evidence_artifact"] == "youtube.webm"
    assert manifest["sha256"] == hashlib.sha256(VIDEO_BYTES).hexdigest()
    assert manifest["persona"] is None
    assert manifest["statute_hook"] is None
    assert manifest["device"]["avd_name"] == "no-id-lab-api35-play"
    assert manifest["recording"] == {"method": "emulator_host_screenrecord", "seconds": 20, "bit_rate": "4M", "fps": 24}


def test_record_skips_apps_that_are_not_installed(recorder, runner):
    result = recorder.record(KICK)

    assert result.status == "skipped-not-installed"
    assert not any("screenrecord" in line for line in runner.lines())


def test_record_reports_failed_recording_and_still_closes_app(recorder, runner):
    runner._responses.insert(0, ("emu screenrecord start", [CommandResult((), 0, "KO: recording already in progress\n", "")]))

    result = recorder.record(YOUTUBE)

    assert result.status == "failed"
    assert "recording already in progress" in result.detail
    assert runner.lines()[-1] == "/adb -s emulator-5554 shell input keyevent KEYCODE_HOME"


def test_record_all_writes_run_summary(recorder, tmp_path):
    results = recorder.record_all([YOUTUBE, KICK])

    assert [r.status for r in results] == ["recorded", "skipped-not-installed"]
    summary = json.loads((tmp_path / "run" / "run.json").read_text())
    assert [entry["status"] for entry in summary["results"]] == ["recorded", "skipped-not-installed"]
    assert summary["results"][0]["manifest"] == "youtube.json"
