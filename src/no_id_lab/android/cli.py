"""Command-line entry point: `uv run no-id-lab-android <command>`."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import sys
from pathlib import Path

from .boot import BootTimeoutError
from .config import ConfigError, load_config
from .emulator import EmulatorError
from .lab import CONFIG_RELATIVE_PATH, AndroidLab, find_repo_root
from .runner import CommandError
from .sdk import ToolNotFoundError

CONFIG_ENV = "NO_ID_LAB_ANDROID_CONFIG"
ENV_EXPORTS = ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_USER_HOME", "ANDROID_EMULATOR_HOME", "ANDROID_AVD_HOME", "JAVA_HOME", "PATH")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="no-id-lab-android", description="No-ID Lab Android emulator lab")
    parser.add_argument("--config", type=Path, help=f"lab config (default: ${CONFIG_ENV} or {CONFIG_RELATIVE_PATH})")
    parser.add_argument("-v", "--verbose", action="store_true", help="log every command that is executed")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="check required tools, SDK paths, and the AVD")
    sub.add_parser("setup", help="install SDK packages, accept licenses, create or update the AVD")
    sub.add_parser("env", help="print shell exports for the lab's Android SDK (eval \"$(... env)\")")

    start = sub.add_parser("start", help="start the emulator and wait for boot")
    _add_display_flags(start)
    start.add_argument("--no-wait", action="store_true", help="return immediately after launching")

    wait = sub.add_parser("wait-boot", help="block until the emulator has finished booting")
    wait.add_argument("--timeout", type=float, help="seconds (default from config)")

    sub.add_parser("status", help="report whether the emulator is running and booted")
    sub.add_parser("stop", help="stop the emulator")

    validate = sub.add_parser("validate", help="start, verify adb, capture properties and a screenshot, stop")
    _add_display_flags(validate)
    validate.add_argument("--keep-running", action="store_true", help="leave the emulator running afterwards")
    return parser


def _add_display_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--headless", dest="headless", action="store_true", default=None, help="no emulator window")
    group.add_argument("--window", dest="headless", action="store_false", help="show the emulator window")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    try:
        config_path = args.config or Path(os.environ.get(CONFIG_ENV) or find_repo_root() / CONFIG_RELATIVE_PATH)
        lab = AndroidLab.from_environment(load_config(config_path))
        return COMMANDS[args.command](lab, args)
    except (ConfigError, ToolNotFoundError, EmulatorError, BootTimeoutError, CommandError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _doctor(lab: AndroidLab, args: argparse.Namespace) -> int:
    print(f"SDK root:  {lab.paths.sdk_root}")
    print(f"AVD home:  {lab.paths.avd_home}")
    print(f"JAVA_HOME: {lab.java_home or '(not found)'}")
    print(f"Image:     {lab.config.system_image_package(lab.machine)}")
    ok = True
    for name, path in lab.tools().items():
        print(f"  {'ok     ' if path else 'MISSING'} {name:<11} {path or ''}")
        ok = ok and path is not None
    problems = lab.avd.validate()
    for problem in problems:
        print(f"  AVD     {problem}")
    if not problems:
        print(f"  ok      avd         {lab.config.avd_name}")
    if not ok or problems:
        print("Run scripts/setup_macos.sh to install missing pieces.", file=sys.stderr)
        return 1
    return 0


def _setup(lab: AndroidLab, args: argparse.Namespace) -> int:
    summary = lab.setup()
    installed = summary["installed_packages"] or ["(nothing new)"]
    print("Installed SDK packages: " + ", ".join(installed))
    print(f"AVD {lab.config.avd_name}: {summary['avd']}")
    return _doctor(lab, args)


def _env(lab: AndroidLab, args: argparse.Namespace) -> int:
    for key in ENV_EXPORTS:
        if key in lab.env:
            print(f"export {key}={shlex.quote(lab.env[key])}")
    return 0


def _start(lab: AndroidLab, args: argparse.Namespace) -> int:
    spawned = lab.start(headless=args.headless, wait=not args.no_wait)
    state = "launched" if args.no_wait else "booted"
    print(f"{lab.emulator.serial} {state if spawned else 'already running'} (log: {lab.emulator.log_path})")
    return 0


def _wait_boot(lab: AndroidLab, args: argparse.Namespace) -> int:
    elapsed = lab.wait_for_boot(timeout=args.timeout)
    print(f"{lab.emulator.serial} booted ({elapsed:.0f}s)")
    return 0


def _status(lab: AndroidLab, args: argparse.Namespace) -> int:
    status = lab.status()
    print(json.dumps(status, indent=2))
    return 0 if status["booted"] else 3


def _stop(lab: AndroidLab, args: argparse.Namespace) -> int:
    print(f"{lab.emulator.serial} {'stopped' if lab.stop() else 'was not running'}")
    return 0


def _validate(lab: AndroidLab, args: argparse.Namespace) -> int:
    report = lab.validate(headless=args.headless, keep_running=args.keep_running)
    print(f"adb reachable: {report.serial} ({report.avd_name})")
    for name, value in report.properties.items():
        print(f"  {name} = {value}")
    print(f"Artifacts: {report.output_dir}")
    print("Android lab validation passed")
    return 0


COMMANDS = {
    "doctor": _doctor,
    "setup": _setup,
    "env": _env,
    "start": _start,
    "wait-boot": _wait_boot,
    "status": _status,
    "stop": _stop,
    "validate": _validate,
}


if __name__ == "__main__":
    sys.exit(main())
