from pathlib import Path

import pytest

from conftest import LAB_CONFIG
from no_id_lab.android.avd import AvdManager, read_ini, write_ini
from no_id_lab.android.config import load_config
from no_id_lab.android.paths import LabPaths


@pytest.fixture
def cfg():
    return load_config(LAB_CONFIG)


@pytest.fixture
def paths(cfg, tmp_path):
    return LabPaths.resolve(cfg, repo_root=tmp_path, environ={})


def fake_avd(paths: LabPaths, name: str, **config) -> Path:
    avd_dir = paths.avd_home / f"{name}.avd"
    avd_dir.mkdir(parents=True, exist_ok=True)
    (paths.avd_home / f"{name}.ini").write_text(f"path={avd_dir}\ntarget=android-35\n")
    base = {
        "image.sysdir.1": "system-images/android-35/google_apis/arm64-v8a/",
        "hw.device.name": "pixel_7",
        "abi.type": "arm64-v8a",
        "tag.id": "google_apis",
    }
    base.update(config)
    write_ini(avd_dir / "config.ini", base)
    return avd_dir


def simulate_avdmanager_create(paths: LabPaths, name: str):
    def create(args):
        fake_avd(paths, name)

    return create


def test_ini_round_trip_preserves_order_and_updates(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("b=1\na = 2\n# comment\n")

    write_ini(path, {"a": "3", "c": "4"})

    assert path.read_text() == "b=1\na=3\n# comment\nc=4\n"
    assert read_ini(path) == {"b": "1", "a": "3", "c": "4"}


def test_create_invokes_avdmanager_with_pinned_profile(cfg, paths, runner):
    avd = AvdManager(cfg, paths, runner, env={"E": "1"}, machine="arm64")

    avd.create()

    call = runner.calls[-1]
    assert call["args"] == (
        str(paths.avdmanager),
        "create",
        "avd",
        "--name",
        "no-id-lab-api35",
        "--package",
        "system-images;android-35;google_apis;arm64-v8a",
        "--device",
        "pixel_7",
        "--sdcard",
        "512M",
        "--force",
    )
    assert call["input"] == "no\n"
    assert call["env"] == {"E": "1"}


def test_ensure_creates_missing_avd_and_applies_hardware(cfg, paths, runner):
    runner.hook("create avd", simulate_avdmanager_create(paths, cfg.avd_name))
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    assert avd.ensure() == "created"

    settings = read_ini(paths.avd_home / f"{cfg.avd_name}.avd" / "config.ini")
    assert settings["hw.ramSize"] == "4096"
    assert settings["hw.keyboard"] == "yes"


def test_ensure_is_idempotent_for_matching_avd(cfg, paths, runner):
    fake_avd(paths, cfg.avd_name, **cfg.hardware)
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    assert avd.ensure() == "unchanged"
    assert runner.calls == []


def test_ensure_updates_drifted_hardware_without_recreating(cfg, paths, runner):
    fake_avd(paths, cfg.avd_name, **{**cfg.hardware, "hw.ramSize": "2048"})
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    assert avd.ensure() == "updated"
    assert runner.calls == []
    assert read_ini(paths.avd_home / f"{cfg.avd_name}.avd" / "config.ini")["hw.ramSize"] == "4096"


def test_ensure_recreates_avd_when_system_image_changes(cfg, paths, runner):
    fake_avd(paths, cfg.avd_name, **{"image.sysdir.1": "system-images/android-34/google_apis/arm64-v8a/"})
    runner.hook("create avd", simulate_avdmanager_create(paths, cfg.avd_name))
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    assert avd.ensure() == "recreated"
    assert any("create avd" in line for line in runner.lines())


def test_validate_reports_missing_avd(cfg, paths, runner):
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    assert avd.validate() == [f"AVD '{cfg.avd_name}' does not exist in {paths.avd_home}"]


def test_validate_reports_profile_drift(cfg, paths, runner):
    fake_avd(paths, cfg.avd_name, **{**cfg.hardware, "hw.device.name": "pixel_4"})
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    problems = avd.validate()

    assert problems == ["hw.device.name is 'pixel_4', expected 'pixel_7'"]


def test_validate_passes_for_matching_avd(cfg, paths, runner):
    fake_avd(paths, cfg.avd_name, **cfg.hardware)
    avd = AvdManager(cfg, paths, runner, env={}, machine="arm64")

    assert avd.validate() == []
