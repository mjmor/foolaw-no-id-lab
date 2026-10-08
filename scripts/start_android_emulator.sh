#!/usr/bin/env bash
# Start the lab emulator and block until it has booted.
# Usage: scripts/start_android_emulator.sh [--headless | --window] [--no-wait]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run no-id-lab-android start "$@"
