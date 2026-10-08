"""Command-line entry point for in-scope app automation: `uv run no-id-lab-apps <command>`."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from .apps import AppsConfig, app_info, load_apps_config
from .boot import BootTimeoutError
from .config import ConfigError, load_config
from .emulator import EmulatorError
from .lab import CONFIG_RELATIVE_PATH, AndroidLab, find_repo_root
from .playstore import PlayStoreInstaller, PlayStoreSignInRequired
from .recording import AppRecorder
from .runner import CommandError
from .sdk import ToolNotFoundError
from .ui import DeviceUi

APPS_CONFIG_RELATIVE_PATH = Path("configs") / "android" / "apps.yaml"
CAPTURES_ENV = "NO_ID_LAB_CAPTURES_DIR"
EXIT_SIGN_IN_REQUIRED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="no-id-lab-apps", description="Install and record the in-scope apps")
    parser.add_argument("--config", type=Path, help=f"lab config (default: {CONFIG_RELATIVE_PATH})")
    parser.add_argument("--apps-config", type=Path, help=f"apps config (default: {APPS_CONFIG_RELATIVE_PATH})")
    parser.add_argument("-v", "--verbose", action="store_true", help="log every command that is executed")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list in-scope apps and, if the emulator is running, their install state")

    install = sub.add_parser("install", help="install apps from the Play Store (requires a signed-in test account)")
    _add_app_filter(install)

    record = sub.add_parser("record", help="record the screen while launching each installed app")
    _add_app_filter(record)
    record.add_argument("--seconds", type=int, help="recording length per app (default from apps config)")
    display = record.add_mutually_exclusive_group()
    display.add_argument("--headless", dest="headless", action="store_true", default=None, help="no emulator window")
    display.add_argument("--window", dest="headless", action="store_false", help="show the emulator window")
    record.add_argument("--keep-running", action="store_true", help="leave the emulator running afterwards")
    return parser


def _add_app_filter(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--app", dest="apps", action="append", metavar="ID", help="limit to this app id (repeatable)")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    try:
        repo_root = find_repo_root()
        lab = AndroidLab.from_environment(load_config(args.config or repo_root / CONFIG_RELATIVE_PATH))
        apps_config = load_apps_config(args.apps_config or repo_root / APPS_CONFIG_RELATIVE_PATH)
        return COMMANDS[args.command](lab, apps_config, repo_root, args)
    except PlayStoreSignInRequired as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_SIGN_IN_REQUIRED
    except (ConfigError, ToolNotFoundError, EmulatorError, BootTimeoutError, CommandError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _list(lab: AndroidLab, apps_config: AppsConfig, repo_root: Path, args: argparse.Namespace) -> int:
    running = lab.emulator.is_running()
    for app in apps_config.apps:
        state = "-"
        if running:
            info = app_info(lab.adb, lab.emulator.serial, app.package)
            state = f"installed {info.version_name or ''}".strip() if info.installed else "not installed"
        print(f"{app.id:<13} {app.name:<13} {app.package:<38} {state}")
    if not running:
        print("(start the emulator to see install state)")
    return 0


def _install(lab: AndroidLab, apps_config: AppsConfig, repo_root: Path, args: argparse.Namespace) -> int:
    apps = apps_config.select(args.apps)
    lab.start()
    serial = lab.emulator.serial
    installer = PlayStoreInstaller(
        lab.adb,
        serial,
        DeviceUi(lab.adb, serial),
        timeout=apps_config.install_timeout_seconds,
        poll_interval=apps_config.install_poll_interval_seconds,
        diagnostics_dir=lab.paths.artifacts_dir / "install" / _timestamp(),
    )
    results = installer.install_all(apps)
    for result in results:
        print(f"{result.app.id:<13} {result.status:<18} {result.version or result.detail}")
    return 1 if any(r.status == "failed" for r in results) else 0


def _record(lab: AndroidLab, apps_config: AppsConfig, repo_root: Path, args: argparse.Namespace) -> int:
    apps = apps_config.select(args.apps)
    if args.seconds:
        apps_config = apps_config.with_overrides(record_seconds=args.seconds)
    captures_root = Path(os.environ.get(CAPTURES_ENV) or repo_root / apps_config.captures_dir)
    output_dir = captures_root / f"android-emulator-{_timestamp()}"
    spawned = lab.start(headless=args.headless)
    try:
        recorder = AppRecorder(lab.adb, lab.emulator.serial, apps_config, lab.config, output_dir, machine=lab.machine)
        results = recorder.record_all(apps)
    finally:
        if spawned and not args.keep_running:
            lab.stop()
    for result in results:
        print(f"{result.app.id:<13} {result.status:<22} {result.video or result.detail}")
    print(f"Captures: {output_dir}")
    return 1 if any(r.status == "failed" for r in results) else 0


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


COMMANDS = {"list": _list, "install": _install, "record": _record}


if __name__ == "__main__":
    sys.exit(main())
