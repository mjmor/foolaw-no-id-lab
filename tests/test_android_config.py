from pathlib import Path

import pytest
import yaml

from conftest import LAB_CONFIG
from no_id_lab.android.config import ConfigError, load_config, resolve_abi


def write_config(tmp_path: Path, **overrides) -> Path:
    data = yaml.safe_load(LAB_CONFIG.read_text())
    for dotted, value in overrides.items():
        node = data
        *parents, leaf = dotted.split("__")
        for key in parents:
            node = node[key]
        if value is None:
            del node[leaf]
        else:
            node[leaf] = value
    path = tmp_path / "lab.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def test_repository_config_pins_android_profile():
    cfg = load_config(LAB_CONFIG)

    assert cfg.api_level == 35
    assert cfg.image_tag == "google_apis"
    assert cfg.architecture == "auto"
    assert cfg.device_profile == "pixel_7"
    assert cfg.avd_name == "no-id-lab-api35"
    assert cfg.headless is False
    assert cfg.sdk_path_policy == "project"
    assert cfg.lab_home == ".android-lab"
    assert cfg.boot_timeout_seconds > 0
    assert cfg.boot_attempts >= 1
    assert cfg.console_port % 2 == 0


@pytest.mark.parametrize(
    ("architecture", "machine", "expected"),
    [
        ("auto", "arm64", "arm64-v8a"),
        ("auto", "aarch64", "arm64-v8a"),
        ("auto", "x86_64", "x86_64"),
        ("arm64-v8a", "x86_64", "arm64-v8a"),
        ("x86_64", "arm64", "x86_64"),
    ],
)
def test_resolve_abi_detects_host_architecture(architecture, machine, expected):
    assert resolve_abi(architecture, machine) == expected


def test_resolve_abi_rejects_unknown_host():
    with pytest.raises(ConfigError, match="host architecture"):
        resolve_abi("auto", "ppc64")


def test_system_image_package_uses_pinned_api_tag_and_abi():
    cfg = load_config(LAB_CONFIG)

    assert cfg.system_image_package("arm64") == "system-images;android-35;google_apis;arm64-v8a"
    assert cfg.system_image_package("x86_64") == "system-images;android-35;google_apis;x86_64"


def test_required_packages_include_tools_and_system_image():
    cfg = load_config(LAB_CONFIG)

    packages = cfg.required_packages("arm64")

    assert packages[0] == "cmdline-tools;23.0"
    assert "platform-tools" in packages
    assert "emulator" in packages
    assert packages[-1] == "system-images;android-35;google_apis;arm64-v8a"


def test_hardware_values_are_strings():
    cfg = load_config(LAB_CONFIG)

    assert cfg.hardware["hw.ramSize"] == "4096"
    assert all(isinstance(v, str) for v in cfg.hardware.values())


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"system_image__tag": "android_tv"}, "system_image.tag"),
        ({"system_image__architecture": "mips"}, "system_image.architecture"),
        ({"sdk__path_policy": "home"}, "sdk.path_policy"),
        ({"emulator__boot_mode": "warm"}, "emulator.boot_mode"),
        ({"emulator__console_port": 5555}, "emulator.console_port"),
        ({"avd_name": "bad name/with slash"}, "avd_name"),
        ({"api_level": None}, "api_level"),
        ({"retries__boot_attempts": 0}, "retries.boot_attempts"),
    ],
)
def test_invalid_config_is_rejected_with_field_name(tmp_path, override, message):
    path = write_config(tmp_path, **override)

    with pytest.raises(ConfigError, match=message):
        load_config(path)
