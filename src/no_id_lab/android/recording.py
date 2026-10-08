"""Record the emulator display while launching each in-scope app.

Uses the emulator's host-side recorder (`adb emu screenrecord`), which captures exactly what the
emulator display shows and writes WebM straight to the host. The in-guest `screenrecord` was
unreliable on this emulator (all-black or stale frames), and is left for a future physical-device tier.

Each recording gets a manifest whose field names follow docs/evidence-schema.md so later phases
can turn captures into observation records. Persona, parental-control, and statute fields stay
null here: this automation does not sign in, configure controls, or interpret what it sees.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .adb import Adb
from .apps import AppInfo, AppsConfig, AppSpec, app_info, close_app, launch_app, time_window
from .config import LabConfig
from .runner import CommandError

log = logging.getLogger(__name__)

RecordingStatus = Literal["recorded", "skipped-not-installed", "failed"]
RECORDING_METHOD = "emulator_host_screenrecord"
FINALIZE_TIMEOUT_SECONDS = 15
DEVICE_TIME_FORMAT = "+%Y-%m-%dT%H:%M:%S%z"


@dataclass(frozen=True)
class RecordingResult:
    app: AppSpec
    status: RecordingStatus
    video: Path | None = None
    manifest: Path | None = None
    detail: str = ""


class AppRecorder:
    def __init__(
        self,
        adb: Adb,
        serial: str,
        apps_config: AppsConfig,
        lab_config: LabConfig,
        output_dir: Path,
        machine: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.adb = adb
        self.serial = serial
        self.apps_config = apps_config
        self.lab_config = lab_config
        self.output_dir = output_dir.resolve()
        self.machine = machine
        self.sleep = sleep
        self.monotonic = monotonic

    def record_all(self, apps: list[AppSpec]) -> list[RecordingResult]:
        results = []
        for app in apps:
            result = self.record(app)
            log.info("%s (%s): %s %s", app.name, app.package, result.status, result.detail or result.video or "")
            results.append(result)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "run_id": self.output_dir.name,
            "created_at": datetime.now(UTC).isoformat(),
            "device": self._device(),
            "results": [
                {
                    "app": r.app.name,
                    "package": r.app.package,
                    "status": r.status,
                    "video": r.video.name if r.video else None,
                    "manifest": r.manifest.name if r.manifest else None,
                    "detail": r.detail,
                }
                for r in results
            ],
        }
        (self.output_dir / "run.json").write_text(json.dumps(summary, indent=2) + "\n")
        return results

    def record(self, app: AppSpec) -> RecordingResult:
        info = app_info(self.adb, self.serial, app.package)
        if not info.installed:
            return RecordingResult(app, "skipped-not-installed", detail="not installed; run scripts/install_android_apps.sh")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        video = self.output_dir / f"{app.id}.webm"
        close_app(self.adb, self.serial, app.package)
        try:
            started = self.monotonic()
            reply = self._emu_screenrecord(
                "start",
                "--time-limit",
                str(self.apps_config.record_seconds + 1),
                "--bit-rate",
                self.apps_config.bit_rate,
                "--fps",
                str(self.apps_config.record_fps),
                str(video),
            )
            if reply.startswith("KO"):
                return RecordingResult(app, "failed", detail=f"emulator recorder refused to start: {reply}")
            self.sleep(self.apps_config.settle_seconds)
            local_time = self.adb.shell(self.serial, "date", DEVICE_TIME_FORMAT, check=False).stdout.strip()
            launch_app(self.adb, self.serial, app.package)
            self.sleep(max(0.0, self.apps_config.record_seconds - (self.monotonic() - started)))
            self._emu_screenrecord("stop")
            if not self._wait_for_file(video):
                return RecordingResult(app, "failed", detail=f"emulator recorder did not write {video}")
            manifest = self._write_manifest(app, info, video, local_time)
            return RecordingResult(app, "recorded", video=video, manifest=manifest)
        except CommandError as exc:
            return RecordingResult(app, "failed", detail=str(exc))
        finally:
            close_app(self.adb, self.serial, app.package)

    def _emu_screenrecord(self, *args: str) -> str:
        return self.adb.run("-s", self.serial, "emu", "screenrecord", *args, check=False).stdout.strip()

    def _wait_for_file(self, video: Path) -> bool:
        """The recorder finalizes the WebM asynchronously after stop; wait until its size settles."""
        waited, last_size = 0.0, -1
        while waited <= FINALIZE_TIMEOUT_SECONDS:
            size = video.stat().st_size if video.exists() else -1
            if size > 0 and size == last_size:
                return True
            last_size = size
            self.sleep(0.5)
            waited += 0.5
        return False

    def _device(self) -> dict[str, object]:
        return {
            "serial": self.serial,
            "avd_name": self.lab_config.avd_name,
            "api_level": self.lab_config.api_level,
            "system_image": self.lab_config.system_image_package(self.machine),
        }

    def _write_manifest(self, app: AppSpec, info: AppInfo, video: Path, local_time: str) -> Path:
        release = self.adb.getprop(self.serial, "ro.build.version.release")
        hour = int(local_time[11:13]) if len(local_time) >= 13 and local_time[11:13].isdigit() else None
        manifest = {
            "observation_id": f"{self.output_dir.name}-{app.id}",
            "capture_type": "app_launch_screen_recording",
            "platform": "android_emulator",
            "app": app.name,
            "package": app.package,
            "app_version": info.version_name,
            "app_version_code": info.version_code,
            "os_version": f"Android {release}" if release else None,
            "persona": None,
            "parental_control_profile": None,
            "parental_control_state": None,
            "local_time": local_time or None,
            "time_window": time_window(hour) if hour is not None else None,
            "engagement_mechanism": None,
            "evidence_artifact": video.name,
            "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
            "statute_hook": None,
            "notes": (
                "App launch recorded by the lab automation with no in-app account, persona, or parental "
                "controls configured. Not yet reviewed or mapped to a statute hook."
            ),
            "device": self._device(),
            "recording": {
                "method": RECORDING_METHOD,
                "seconds": self.apps_config.record_seconds,
                "bit_rate": self.apps_config.bit_rate,
                "fps": self.apps_config.record_fps,
            },
        }
        path = video.with_suffix(".json")
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        return path
