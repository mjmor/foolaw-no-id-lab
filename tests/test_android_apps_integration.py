"""Integration tests for app automation against the real emulator.

Excluded from the default run. Run with: uv run pytest -m integration
YouTube ships with the Google Play image, so recording can be checked without a Play Store sign-in.
"""

import json

import pytest

from conftest import LAB_CONFIG, REPO_ROOT
from no_id_lab.android.apps import app_info, load_apps_config
from no_id_lab.android.config import load_config
from no_id_lab.android.lab import AndroidLab
from no_id_lab.android.recording import AppRecorder

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def running_lab():
    lab = AndroidLab.from_environment(load_config(LAB_CONFIG))
    spawned = lab.start(headless=True)
    yield lab
    if spawned:
        lab.stop()


def test_preinstalled_youtube_is_detected(running_lab):
    info = app_info(running_lab.adb, running_lab.emulator.serial, "com.google.android.youtube")

    assert info.installed
    assert info.version_name


def test_recording_youtube_launch_produces_video_and_manifest(running_lab, tmp_path):
    apps = load_apps_config(REPO_ROOT / "configs" / "android" / "apps.yaml")
    recorder = AppRecorder(
        running_lab.adb,
        running_lab.emulator.serial,
        apps.with_overrides(record_seconds=5),
        running_lab.config,
        output_dir=tmp_path,
        machine=running_lab.machine,
    )

    result = recorder.record(apps.select(["youtube"])[0])

    assert result.status == "recorded", result.detail
    assert result.video.stat().st_size > 10_000
    assert result.video.read_bytes()[4:8] == b"ftyp"
    assert json.loads(result.manifest.read_text())["os_version"] == "Android 15"
