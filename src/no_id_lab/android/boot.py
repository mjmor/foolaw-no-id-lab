"""Boot-state detection for a device reachable through adb."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from .adb import Adb
from .runner import CommandError

log = logging.getLogger(__name__)


class BootTimeoutError(TimeoutError):
    pass


def is_booted(adb: Adb, serial: str) -> bool:
    """True once adb sees the device, Android reports boot completion, the package manager
    answers, and a window has input focus (the UI is ready for screenshots and automation)."""
    try:
        if adb.devices().get(serial) != "device":
            return False
        if adb.getprop(serial, "sys.boot_completed") != "1":
            return False
        if not adb.shell(serial, "pm", "path", "android", check=False).stdout.startswith("package:"):
            return False
        return is_ui_ready(adb, serial)
    except CommandError:
        return False


def is_ui_ready(adb: Adb, serial: str) -> bool:
    output = adb.shell(serial, "dumpsys", "window", "displays", check=False).stdout
    return any(
        line.strip().startswith("mCurrentFocus=") and line.strip() != "mCurrentFocus=null"
        for line in output.splitlines()
    )


def wait_for_boot(
    adb: Adb,
    serial: str,
    timeout: float,
    poll_interval: float,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> float:
    """Block until `serial` has fully booted; returns elapsed seconds."""
    started = monotonic()
    while True:
        if is_booted(adb, serial):
            elapsed = monotonic() - started
            log.info("%s booted in %.0fs", serial, elapsed)
            return elapsed
        if monotonic() - started >= timeout:
            raise BootTimeoutError(f"{serial} did not finish booting within {timeout:.0f}s")
        sleep(poll_interval)
