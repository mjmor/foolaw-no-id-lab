"""Minimal UI inspection and input via `uiautomator dump` and `input tap`.

Enough to drive a few known buttons without an Appium server. Richer flows should move to
Appium/UiAutomator2 via `automation.DeviceTarget`.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .adb import Adb

REMOTE_DUMP = "/data/local/tmp/no-id-lab-ui.xml"
BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


@dataclass(frozen=True)
class UiNode:
    text: str
    content_desc: str
    resource_id: str
    class_name: str
    enabled: bool
    bounds: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bounds
        return (x1 + x2) // 2, (y1 + y2) // 2


def parse_ui_dump(xml: str) -> list[UiNode]:
    nodes = []
    for element in ET.fromstring(xml.strip()).iter("node"):
        match = BOUNDS.match(element.get("bounds", ""))
        nodes.append(
            UiNode(
                text=element.get("text", ""),
                content_desc=element.get("content-desc", ""),
                resource_id=element.get("resource-id", ""),
                class_name=element.get("class", ""),
                enabled=element.get("enabled", "true") == "true",
                bounds=tuple(int(v) for v in match.groups()) if match else (0, 0, 0, 0),
            )
        )
    return nodes


def find_node(nodes: list[UiNode], *labels: str) -> UiNode | None:
    """First enabled node whose text (preferred) or content description exactly equals one of `labels`."""
    for attribute in ("text", "content_desc"):
        for label in labels:
            for node in nodes:
                if node.enabled and getattr(node, attribute) == label:
                    return node
    return None


class DeviceUi:
    def __init__(self, adb: Adb, serial: str) -> None:
        self.adb = adb
        self.serial = serial

    def dump(self) -> list[UiNode]:
        return parse_ui_dump(self.dump_xml())

    def dump_xml(self) -> str:
        self.adb.shell(self.serial, "uiautomator", "dump", REMOTE_DUMP)
        return self.adb.shell(self.serial, "cat", REMOTE_DUMP).stdout

    def tap(self, node: UiNode) -> None:
        x, y = node.center
        self.adb.shell(self.serial, "input", "tap", str(x), str(y))

    def focused_window(self) -> str:
        output = self.adb.shell(self.serial, "dumpsys", "window", "displays", check=False).stdout
        for line in output.splitlines():
            if line.strip().startswith("mCurrentFocus="):
                return line.strip().removeprefix("mCurrentFocus=")
        return ""
