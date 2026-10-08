#!/usr/bin/env bash
# Install the in-scope apps (configs/android/apps.yaml) from the Play Store on the lab emulator.
# Starts the emulator if needed and leaves it running. The Play Store must already be signed in
# with the lab's controlled test Google account (exit code 2 if not). See docs/android-app-automation.md.
# Usage: scripts/install_android_apps.sh [--app ID ...]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run no-id-lab-apps install "$@"
