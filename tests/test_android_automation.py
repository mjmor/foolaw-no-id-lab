from conftest import LAB_CONFIG
from no_id_lab.android.automation import DeviceTarget
from no_id_lab.android.config import load_config


def test_device_target_from_config():
    target = DeviceTarget.from_config(load_config(LAB_CONFIG))

    assert target.serial == "emulator-5554"
    assert target.avd_name == "no-id-lab-api35"
    assert target.api_level == 35


def test_uiautomator2_capabilities_target_the_lab_emulator_without_app():
    caps = DeviceTarget(serial="emulator-5554", avd_name="lab", api_level=35).uiautomator2_capabilities()

    assert caps == {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:udid": "emulator-5554",
        "appium:avd": "lab",
        "appium:platformVersion": "15",
        "appium:noReset": True,
    }


def test_capabilities_merge_caller_extras():
    caps = DeviceTarget(serial="emulator-5554", avd_name="lab", api_level=35).uiautomator2_capabilities(
        {"appium:appPackage": "com.example"}
    )

    assert caps["appium:appPackage"] == "com.example"
