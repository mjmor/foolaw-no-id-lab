from pathlib import Path

from no_id_lab.android.adb import Adb
from no_id_lab.android.ui import DeviceUi, find_node, parse_ui_dump

SERIAL = "emulator-5554"

LISTING_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" content-desc="" enabled="true" bounds="[0,0][1080,2400]">
    <node index="0" text="Instagram" resource-id="" class="android.widget.TextView" content-desc="" enabled="true" bounds="[200,300][800,380]" />
    <node index="1" text="" resource-id="" class="android.view.View" content-desc="Install" enabled="true" bounds="[48,900][1032,1020]">
      <node index="0" text="Install" resource-id="" class="android.widget.TextView" content-desc="" enabled="true" bounds="[480,940][600,980]" />
    </node>
    <node index="2" text="Install on more devices" resource-id="" class="android.widget.TextView" content-desc="" enabled="true" bounds="[48,1100][1032,1160]" />
    <node index="3" text="Uninstall" resource-id="" class="android.widget.TextView" content-desc="" enabled="false" bounds="[0,0][10,10]" />
  </node>
</hierarchy>
"""


def test_parse_ui_dump_reads_text_desc_and_bounds():
    nodes = parse_ui_dump(LISTING_XML)

    install_text = next(n for n in nodes if n.text == "Install")
    assert install_text.bounds == (480, 940, 600, 980)
    assert install_text.center == (540, 960)
    assert any(n.content_desc == "Install" for n in nodes)


def test_find_node_matches_exact_text_or_description_and_skips_disabled():
    nodes = parse_ui_dump(LISTING_XML)

    assert find_node(nodes, "Install").text == "Install"
    assert find_node(nodes, "Install on more") is None
    assert find_node(nodes, "Uninstall") is None
    assert find_node(nodes, "Missing", "Install") is not None


def test_device_ui_dumps_via_uiautomator_and_taps_node_center(runner):
    runner.on("cat /data/local/tmp/no-id-lab-ui.xml", LISTING_XML)
    ui = DeviceUi(Adb(Path("/adb"), runner, env={}), SERIAL)

    nodes = ui.dump()
    ui.tap(find_node(nodes, "Install"))

    lines = runner.lines()
    assert "/adb -s emulator-5554 shell uiautomator dump /data/local/tmp/no-id-lab-ui.xml" in lines
    assert "/adb -s emulator-5554 shell input tap 540 960" in lines


def test_device_ui_reports_focused_window(runner):
    runner.on("dumpsys window displays", "  mCurrentFocus=Window{1 u0 com.android.vending/com.google.android.finsky.unauthenticated.activity.UnauthenticatedMainActivity}\n")
    ui = DeviceUi(Adb(Path("/adb"), runner, env={}), SERIAL)

    assert ui.focused_window().endswith("UnauthenticatedMainActivity}")
