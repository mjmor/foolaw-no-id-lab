"""Install apps from the Google Play Store app on the emulator by driving its listing page.

Requires the Play Store to be signed in with a controlled test account. Signing in is a manual,
one-time step (see docs/android-app-automation.md); this module never handles credentials.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .adb import Adb
from .apps import AppSpec, app_info
from .runner import CommandError
from .ui import DeviceUi, UiNode, find_node

log = logging.getLogger(__name__)

PLAY_STORE_PACKAGE = "com.android.vending"
INSTALL_LABELS = ("Install",)
INSTALLED_LABELS = ("Open", "Play", "Uninstall", "Update")
SIGN_IN_LABELS = ("Sign in",)
LISTING_TIMEOUT_SECONDS = 60

InstallStatus = Literal["installed", "already-installed", "failed"]


class PlayStoreSignInRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class InstallResult:
    app: AppSpec
    status: InstallStatus
    version: str | None = None
    detail: str = ""


class PlayStoreInstaller:
    def __init__(
        self,
        adb: Adb,
        serial: str,
        ui: DeviceUi,
        timeout: float,
        poll_interval: float,
        diagnostics_dir: Path,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        listing_timeout: float = LISTING_TIMEOUT_SECONDS,
    ) -> None:
        self.adb = adb
        self.serial = serial
        self.ui = ui
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.diagnostics_dir = diagnostics_dir
        self.sleep = sleep
        self.monotonic = monotonic
        self.listing_timeout = listing_timeout

    def install_all(self, apps: list[AppSpec]) -> list[InstallResult]:
        """Install each app; a per-app failure does not stop the run, a signed-out Play Store does."""
        results = []
        for app in apps:
            result = self.install(app)
            log.info("%s (%s): %s %s", app.name, app.package, result.status, result.detail or result.version or "")
            results.append(result)
        return results

    def install(self, app: AppSpec) -> InstallResult:
        info = app_info(self.adb, self.serial, app.package)
        if info.installed:
            return InstallResult(app, "already-installed", info.version_name)
        self._open_listing(app)
        button = self._wait_for_install_button(app)
        if button is None:
            return self._fail(app, "No Install button on the Play Store listing (app may be incompatible or unavailable)")
        log.info("Installing %s from the Play Store", app.name)
        self.ui.tap(button)
        return self._wait_for_package(app)

    def _open_listing(self, app: AppSpec) -> None:
        self.adb.shell(
            self.serial,
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            f"market://details?id={app.package}",
            "-p",
            PLAY_STORE_PACKAGE,
        )

    def _wait_for_install_button(self, app: AppSpec) -> UiNode | None:
        started = self.monotonic()
        while True:
            self._raise_if_signed_out()
            try:
                nodes = self.ui.dump()
            except (CommandError, ValueError):
                nodes = []
            if find_node(nodes, *SIGN_IN_LABELS) and not find_node(nodes, *INSTALL_LABELS):
                self._raise_sign_in_required()
            button = find_node(nodes, *INSTALL_LABELS)
            if button is not None:
                return button
            if find_node(nodes, *INSTALLED_LABELS) or self.monotonic() - started >= self.listing_timeout:
                return None
            self.sleep(self.poll_interval)

    def _wait_for_package(self, app: AppSpec) -> InstallResult:
        started = self.monotonic()
        while self.monotonic() - started < self.timeout:
            self.sleep(self.poll_interval)
            info = app_info(self.adb, self.serial, app.package)
            if info.installed:
                return InstallResult(app, "installed", info.version_name)
        return self._fail(app, f"Install timed out after {self.timeout:.0f}s")

    def _raise_if_signed_out(self) -> None:
        if "unauthenticated" in self.ui.focused_window().lower():
            self._raise_sign_in_required()

    def _raise_sign_in_required(self) -> None:
        raise PlayStoreSignInRequired(
            "Sign in to the Play Store with the lab's controlled test Google account first: start the emulator "
            "with scripts/start_android_emulator.sh --window, open Play Store, and sign in. Then rerun the install."
        )

    def _fail(self, app: AppSpec, detail: str) -> InstallResult:
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        try:
            (self.diagnostics_dir / f"{app.id}-ui.xml").write_text(self.ui.dump_xml())
            self.adb.screenshot(self.serial, self.diagnostics_dir / f"{app.id}-screen.png")
            detail += f" (diagnostics: {self.diagnostics_dir})"
        except CommandError as exc:
            log.warning("Could not capture diagnostics for %s: %s", app.id, exc)
        return InstallResult(app, "failed", detail=detail)
