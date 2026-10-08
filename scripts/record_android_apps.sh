#!/usr/bin/env bash
# Launch each installed in-scope app while recording the screen. Videos and manifests are written
# to captures/android-emulator-<timestamp>/ (gitignored; override with NO_ID_LAB_CAPTURES_DIR).
# Usage: scripts/record_android_apps.sh [--app ID ...] [--seconds N] [--headless | --window] [--keep-running]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run no-id-lab-apps record "$@"
