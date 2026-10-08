"""Record the device screen while launching each in-scope app.

Each recording gets a manifest whose field names follow docs/evidence-schema.md so later phases
can turn captures into observation records. Persona, parental-control, and statute fields stay
null here: this automation does not sign in, configure controls, or interpret what it sees.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
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
RECORDER_START_TIMEOUT_SECONDS = 10
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
    ) -> None:
        self.adb = adb
        self.serial = serial
        self.apps_config = apps_config
        self.lab_config = lab_config
        self.output_dir = output_dir
        self.machine = machine
        self.sleep = sleep

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
        remote = f"/data/local/tmp/no-id-lab-{app.id}.mp4"
        video = self.output_dir / f"{app.id}.mp4"
        close_app(self.adb, self.serial, app.package)
        errors: list[Exception] = []
        recorder = threading.Thread(target=self._screenrecord, args=(remote, errors), daemon=True)
        try:
            recorder.start()
            self._wait_for_recorder(recorder)
            self.sleep(self.apps_config.settle_seconds)
            local_time = self.adb.shell(self.serial, "date", DEVICE_TIME_FORMAT, check=False).stdout.strip()
            launch_app(self.adb, self.serial, app.package)
            recorder.join(self.apps_config.record_seconds + 60)
            if errors:
                return RecordingResult(app, "failed", detail=str(errors[0]))
            self.adb.run("-s", self.serial, "pull", remote, str(video))
            manifest = self._write_manifest(app, info, video, local_time)
            return RecordingResult(app, "recorded", video=video, manifest=manifest)
        except CommandError as exc:
            return RecordingResult(app, "failed", detail=str(exc))
        finally:
            self.adb.shell(self.serial, "rm", "-f", remote, check=False)
            close_app(self.adb, self.serial, app.package)

    def _screenrecord(self, remote: str, errors: list[Exception]) -> None:
        config = self.apps_config
        args = ["screenrecord", "--time-limit", str(config.record_seconds), "--bit-rate", config.bit_rate]
        if config.timestamp_overlay:
            args.append("--bugreport")
        try:
            self.adb.run("-s", self.serial, "shell", *args, remote, timeout=config.record_seconds + 30)
        except CommandError as exc:
            errors.append(exc)

    def _wait_for_recorder(self, recorder: threading.Thread) -> None:
        """Launch only once screenrecord is running, so the app's first frames are captured."""
        waited = 0.0
        while recorder.is_alive() and waited < RECORDER_START_TIMEOUT_SECONDS:
            if self.adb.shell(self.serial, "pidof", "screenrecord", check=False).stdout.strip():
                return
            self.sleep(0.25)
            waited += 0.25

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
                "seconds": self.apps_config.record_seconds,
                "settle_seconds": self.apps_config.settle_seconds,
                "bit_rate": self.apps_config.bit_rate,
                "timestamp_overlay": self.apps_config.timestamp_overlay,
            },
        }
        path = video.with_suffix(".json")
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        return path
