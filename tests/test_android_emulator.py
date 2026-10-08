import json

import pytest

from conftest import LAB_CONFIG
from no_id_lab.android.adb import Adb, parse_adb_devices
from no_id_lab.android.boot import BootTimeoutError, is_ui_ready, wait_for_boot
from no_id_lab.android.config import load_config
from no_id_lab.android.emulator import Emulator, EmulatorError, build_start_command
from no_id_lab.android.lab import AndroidLab
from no_id_lab.android.paths import LabPaths

SERIAL = "emulator-5554"
NO_DEVICES = "List of devices attached\n\n"
OFFLINE = f"List of devices attached\n{SERIAL}\toffline\n\n"
ONLINE = f"List of devices attached\n{SERIAL}\tdevice\n\n"
NO_FOCUS = "  mCurrentFocus=null\n"
LAUNCHER_FOCUS = "  mCurrentFocus=Window{1 u0 com.google.android.apps.nexuslauncher/.NexusLauncherActivity}\n"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def cfg():
    return load_config(LAB_CONFIG)


@pytest.fixture
def paths(cfg, tmp_path):
    return LabPaths.resolve(cfg, repo_root=tmp_path, environ={})


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def adb(paths, runner):
    return Adb(paths.adb, runner, env={})


def make_emulator(cfg, paths, runner, adb, clock):
    return Emulator(cfg, paths, runner, adb, env={"E": "1"}, sleep=clock.sleep, monotonic=clock.monotonic)


def test_parse_adb_devices():
    output = "* daemon started successfully\nList of devices attached\nemulator-5554\tdevice\nemulator-5556\toffline\n\n"

    assert parse_adb_devices(output) == {"emulator-5554": "device", "emulator-5556": "offline"}


def test_windowed_start_command(cfg, paths):
    command = build_start_command(cfg, paths, headless=False)

    assert command == [
        str(paths.emulator),
        "-avd",
        "no-id-lab-api35",
        "-port",
        "5554",
        "-gpu",
        "auto",
        "-no-snapshot",
    ]


def test_headless_start_command(cfg, paths):
    command = build_start_command(cfg, paths, headless=True)

    assert command[:5] == [str(paths.emulator), "-avd", "no-id-lab-api35", "-port", "5554"]
    assert {"-no-window", "-no-audio", "-no-boot-anim"} <= set(command)
    assert command[command.index("-gpu") + 1] == "swiftshader_indirect"


def test_quick_boot_mode_keeps_snapshots(cfg, paths):
    command = build_start_command(cfg.with_overrides(boot_mode="quick"), paths, headless=False)

    assert "-no-snapshot" not in command


def test_wait_for_boot_polls_until_boot_completed(adb, runner, clock):
    runner.on("devices", NO_DEVICES, OFFLINE, ONLINE)
    runner.on("getprop sys.boot_completed", "", "0", "1")
    runner.on("pm path android", "package:/system/framework/framework-res.apk\n")
    runner.on("dumpsys window", NO_FOCUS, LAUNCHER_FOCUS)

    elapsed = wait_for_boot(adb, SERIAL, timeout=60, poll_interval=2, sleep=clock.sleep, monotonic=clock.monotonic)

    assert elapsed == clock.now
    assert sum("getprop sys.boot_completed" in line for line in runner.lines()) == 4
    assert sum("dumpsys window" in line for line in runner.lines()) == 2


def test_ui_not_ready_until_a_window_has_focus(adb, runner):
    runner.on("dumpsys window", NO_FOCUS)

    assert is_ui_ready(adb, SERIAL) is False


def test_wait_for_boot_times_out(adb, runner, clock):
    runner.on("devices", OFFLINE)

    with pytest.raises(BootTimeoutError, match="emulator-5554"):
        wait_for_boot(adb, SERIAL, timeout=10, poll_interval=2, sleep=clock.sleep, monotonic=clock.monotonic)


def test_start_spawns_emulator_detached_and_records_pid(cfg, paths, runner, adb, clock):
    runner.on("devices", NO_DEVICES)
    emulator = make_emulator(cfg, paths, runner, adb, clock)

    pid = emulator.start(headless=True)

    assert pid == 4242
    spawn = runner.spawned[0]
    assert spawn["args"] == tuple(build_start_command(cfg, paths, headless=True))
    assert spawn["env"] == {"E": "1"}
    assert spawn["log_path"] == paths.logs_dir / "emulator-no-id-lab-api35.log"
    assert emulator.pid_file.read_text() == "4242"


def test_start_refuses_when_serial_already_in_use(cfg, paths, runner, adb, clock):
    runner.on("devices", ONLINE)
    emulator = make_emulator(cfg, paths, runner, adb, clock)

    with pytest.raises(EmulatorError, match="already running"):
        emulator.start(headless=True)
    assert runner.spawned == []


def test_stop_kills_running_emulator_and_waits_for_exit(cfg, paths, runner, adb, clock):
    runner.on("devices", ONLINE, ONLINE, NO_DEVICES)
    emulator = make_emulator(cfg, paths, runner, adb, clock)
    emulator.pid_file.parent.mkdir(parents=True)
    emulator.pid_file.write_text("4242")

    assert emulator.stop() is True

    assert f"{paths.adb} -s {SERIAL} emu kill" in runner.lines()
    assert not emulator.pid_file.exists()


def test_stop_is_noop_when_not_running(cfg, paths, runner, adb, clock):
    runner.on("devices", NO_DEVICES)
    emulator = make_emulator(cfg, paths, runner, adb, clock)

    assert emulator.stop() is False
    assert not any("emu kill" in line for line in runner.lines())


def make_lab(cfg, paths, runner, clock):
    avd_dir = paths.avd_home / f"{cfg.avd_name}.avd"
    avd_dir.mkdir(parents=True)
    (paths.avd_home / f"{cfg.avd_name}.ini").write_text(f"path={avd_dir}\n")
    (avd_dir / "config.ini").write_text("")
    return AndroidLab(cfg, paths, runner, env={}, java_home=None, machine="arm64", sleep=clock.sleep, monotonic=clock.monotonic)


def test_lab_start_waits_for_boot(cfg, paths, runner, clock):
    runner.on("devices", NO_DEVICES, NO_DEVICES, ONLINE)
    runner.on("getprop sys.boot_completed", "1")
    runner.on("pm path android", "package:/system/framework/framework-res.apk\n")
    runner.on("dumpsys window", LAUNCHER_FOCUS)
    lab = make_lab(cfg, paths, runner, clock)

    lab.start(headless=True)

    assert len(runner.spawned) == 1
    assert any("getprop sys.boot_completed" in line for line in runner.lines())


def test_lab_start_retries_after_boot_timeout(cfg, paths, runner, clock):
    cfg = cfg.with_overrides(boot_timeout_seconds=4, boot_attempts=2)
    runner.on("devices", NO_DEVICES, NO_DEVICES, OFFLINE, OFFLINE, OFFLINE, OFFLINE, NO_DEVICES, NO_DEVICES, ONLINE)
    runner.on("getprop sys.boot_completed", "1")
    runner.on("pm path android", "package:x\n")
    runner.on("dumpsys window", LAUNCHER_FOCUS)
    lab = make_lab(cfg, paths, runner, clock)

    lab.start(headless=True)

    assert len(runner.spawned) == 2


def test_lab_validate_runs_full_lifecycle_and_writes_artifacts(cfg, paths, runner, clock):
    runner.on("devices", NO_DEVICES, NO_DEVICES, ONLINE, ONLINE, ONLINE, ONLINE, NO_DEVICES)
    runner.on("getprop sys.boot_completed", "1")
    runner.on("pm path android", "package:x\n")
    runner.on("dumpsys window", LAUNCHER_FOCUS)
    runner.on("getprop ro.build.version.sdk", "35\n")
    runner.on("getprop ro.product.cpu.abi", "arm64-v8a\n")
    runner.on("getprop ro.build.version.release", "15\n")
    runner.on("getprop ro.product.model", "sdk_gphone64_arm64\n")
    runner.on("getprop ro.kernel.qemu", "1\n")

    def pull(args):
        dest = args[-1]
        open(dest, "wb").write(b"\x89PNG")

    runner.hook(" pull ", pull)
    lab = make_lab(cfg, paths, runner, clock)

    report = lab.validate(headless=True)

    assert report.serial == SERIAL
    assert report.properties["ro.build.version.sdk"] == "35"
    assert report.screenshot.read_bytes() == b"\x89PNG"
    assert report.output_dir.parent == paths.artifacts_dir / "validation"
    saved = json.loads((report.output_dir / "device-properties.json").read_text())
    assert saved["serial"] == SERIAL
    assert saved["avd_name"] == cfg.avd_name
    assert f"{paths.adb} -s {SERIAL} shell screencap -p /data/local/tmp/no-id-lab-screenshot.png" in runner.lines()
    assert f"{paths.adb} -s {SERIAL} emu kill" in runner.lines()


def test_lab_validate_fails_when_api_level_mismatches(cfg, paths, runner, clock):
    runner.on("devices", NO_DEVICES, NO_DEVICES, ONLINE, ONLINE, ONLINE, ONLINE, NO_DEVICES)
    runner.on("getprop sys.boot_completed", "1")
    runner.on("pm path android", "package:x\n")
    runner.on("dumpsys window", LAUNCHER_FOCUS)
    runner.on("getprop ro.build.version.sdk", "34\n")
    lab = make_lab(cfg, paths, runner, clock)

    with pytest.raises(EmulatorError, match="API level"):
        lab.validate(headless=True)
    assert f"{paths.adb} -s {SERIAL} emu kill" in runner.lines()
