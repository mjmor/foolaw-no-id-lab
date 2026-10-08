#!/usr/bin/env bash
# End-to-end integration check: verifies tools and the AVD, boots the emulator
# (headless unless --window is given), confirms adb reachability, captures device
# properties and a screenshot under .android-lab/artifacts/validation/, then stops it.
# Usage: scripts/validate_android_lab.sh [--window | --headless] [--keep-running]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

args=("$@")
case " ${args[*]-} " in
  *" --window "*|*" --headless "*) ;;
  *) args=(--headless "${args[@]+"${args[@]}"}") ;;
esac

uv run no-id-lab-android doctor
exec uv run no-id-lab-android validate "${args[@]}"
