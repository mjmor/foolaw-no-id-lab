#!/usr/bin/env bash
# Stop the lab emulator. Exits 0 if it was not running.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run no-id-lab-android stop "$@"
