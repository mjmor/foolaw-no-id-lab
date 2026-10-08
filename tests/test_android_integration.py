"""Integration tests that exercise the real Android SDK and emulator.

Excluded from the default run. Run with: uv run pytest -m integration
Requires scripts/setup_macos.sh to have completed on this machine.
"""

import pytest

from conftest import LAB_CONFIG
from no_id_lab.android.config import load_config
from no_id_lab.android.lab import AndroidLab
from no_id_lab.android.sdk import discover_tools

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def lab():
    return AndroidLab.from_environment(load_config(LAB_CONFIG))


def test_required_tools_are_discoverable(lab):
    tools = discover_tools(lab.paths, lab.java_home)

    missing = [name for name, path in tools.items() if path is None]
    assert missing == []


def test_sdk_paths_are_configured(lab):
    assert lab.paths.sdk_root.is_dir()
    assert lab.env["ANDROID_HOME"] == str(lab.paths.sdk_root)
    assert lab.env["ANDROID_AVD_HOME"] == str(lab.paths.avd_home)


def test_avd_matches_configuration(lab):
    assert lab.avd.validate() == []


def test_emulator_boots_is_reachable_via_adb_and_stops(lab):
    if lab.emulator.is_running():
        pytest.skip(f"{lab.emulator.serial} is already running; stop it before running integration tests")

    report = lab.validate(headless=True)

    assert report.properties["sys.boot_completed"] == "1"
    assert report.properties["ro.build.version.sdk"] == str(lab.config.api_level)
    assert report.screenshot.stat().st_size > 0
    assert lab.adb.devices().get(lab.emulator.serial) is None
