from pathlib import Path

import pytest

from no_id_lab.android.adb import Adb
from no_id_lab.android.apps import AppSpec
from no_id_lab.android.playstore import PlayStoreInstaller, PlayStoreSignInRequired
from no_id_lab.android.ui import DeviceUi

SERIAL = "emulator-5554"
INSTAGRAM = AppSpec(id="instagram", name="Instagram", package="com.instagram.android")
KICK = AppSpec(id="kick", name="Kick", package="com.kick.mobile")
SIGNED_IN_FOCUS = "  mCurrentFocus=Window{1 u0 com.android.vending/com.google.android.finsky.activities.MainActivity}\n"
SIGNED_OUT_FOCUS = (
    "  mCurrentFocus=Window{1 u0 com.android.vending/"
    "com.google.android.finsky.unauthenticated.activity.UnauthenticatedMainActivity}\n"
)


def ui_xml(*texts: str) -> str:
    nodes = "".join(
        f'<node text="{t}" resource-id="" class="android.widget.TextView" content-desc="" enabled="true" '
        f'bounds="[100,{200 + i * 100}][300,{260 + i * 100}]" />'
        for i, t in enumerate(texts)
    )
    return f'<?xml version="1.0"?><hierarchy rotation="0">{nodes}</hierarchy>'


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def installer(runner, clock, tmp_path):
    def pull(args):
        Path(args[-1]).write_bytes(b"\x89PNG")

    runner.hook(" pull ", pull)
    adb = Adb(Path("/adb"), runner, env={})
    return PlayStoreInstaller(
        adb,
        SERIAL,
        DeviceUi(adb, SERIAL),
        timeout=60,
        poll_interval=5,
        diagnostics_dir=tmp_path / "diagnostics",
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def test_already_installed_app_is_not_reinstalled(installer, runner):
    runner.on("pm path com.instagram.android", "package:/data/app/base.apk\n")
    runner.on("dumpsys package com.instagram.android", "    versionName=400.0.0\n")

    result = installer.install(INSTAGRAM)

    assert result.status == "already-installed"
    assert result.version == "400.0.0"
    assert not any("market://" in line for line in runner.lines())


def test_install_opens_listing_taps_install_and_waits_for_package(installer, runner):
    runner.on("pm path com.instagram.android", "", "", "", "package:/data/app/base.apk\n")
    runner.on("dumpsys package com.instagram.android", "    versionName=400.0.0\n")
    runner.on("dumpsys window displays", SIGNED_IN_FOCUS)
    runner.on("cat /data/local/tmp/no-id-lab-ui.xml", ui_xml("Instagram", "Install"))

    result = installer.install(INSTAGRAM)

    assert result.status == "installed"
    assert result.version == "400.0.0"
    lines = runner.lines()
    assert (
        "/adb -s emulator-5554 shell am start -a android.intent.action.VIEW "
        "-d market://details?id=com.instagram.android -p com.android.vending"
    ) in lines
    assert "/adb -s emulator-5554 shell input tap 200 330" in lines


def test_signed_out_play_store_stops_with_instructions(installer, runner):
    runner.on("pm path", "")
    runner.on("dumpsys window displays", SIGNED_OUT_FOCUS)
    runner.on("cat /data/local/tmp/no-id-lab-ui.xml", ui_xml("Sign in"))

    with pytest.raises(PlayStoreSignInRequired, match="Sign in to the Play Store"):
        installer.install_all([INSTAGRAM, KICK])
    assert not any("input tap" in line for line in runner.lines())


def test_listing_without_install_button_fails_and_saves_diagnostics(installer, runner, tmp_path):
    runner.on("pm path", "")
    runner.on("dumpsys window displays", SIGNED_IN_FOCUS)
    runner.on("cat /data/local/tmp/no-id-lab-ui.xml", ui_xml("Kick", "Your device isn't compatible with this version."))

    result = installer.install(KICK)

    assert result.status == "failed"
    assert "Install button" in result.detail
    assert (tmp_path / "diagnostics" / "kick-ui.xml").read_text().startswith("<?xml")
    assert (tmp_path / "diagnostics" / "kick-screen.png").exists()


def test_install_that_never_completes_times_out(installer, runner):
    runner.on("pm path com.kick.mobile", "")
    runner.on("dumpsys window displays", SIGNED_IN_FOCUS)
    runner.on("cat /data/local/tmp/no-id-lab-ui.xml", ui_xml("Kick", "Install"))

    result = installer.install(KICK)

    assert result.status == "failed"
    assert "timed out" in result.detail


def test_install_all_continues_after_a_single_failure(installer, runner):
    runner.on("pm path com.kick.mobile", "")
    runner.on("pm path com.instagram.android", "package:/data/app/base.apk\n")
    runner.on("dumpsys window displays", SIGNED_IN_FOCUS)
    runner.on("cat /data/local/tmp/no-id-lab-ui.xml", ui_xml("Kick"))

    results = installer.install_all([KICK, INSTAGRAM])

    assert [r.status for r in results] == ["failed", "already-installed"]
