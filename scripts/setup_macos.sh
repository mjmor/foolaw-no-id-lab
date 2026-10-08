#!/usr/bin/env bash
# Idempotent macOS bootstrap for the No-ID Lab Android emulator lab.
#   1. Installs Brewfile dependencies (uv, openjdk@21, Android command-line tools).
#   2. Syncs the pinned Python environment with uv.
#   3. Installs pinned SDK packages, accepts licenses, and creates/updates the AVD
#      described in configs/android/lab.yaml.
# Safe to run repeatedly. Usage: scripts/setup_macos.sh [--skip-brew]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

skip_brew=false
for arg in "$@"; do
  case "$arg" in
    --skip-brew) skip_brew=true ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "This setup script supports macOS only."

if [[ "$skip_brew" == false ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
      if [[ -x "$candidate" ]]; then eval "$("$candidate" shellenv)"; break; fi
    done
  fi
  command -v brew >/dev/null 2>&1 || die "Homebrew is required. Install it from https://brew.sh:
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"
then rerun scripts/setup_macos.sh"

  step "Homebrew dependencies (Brewfile)"
  if brew bundle check --file="$REPO_ROOT/Brewfile" >/dev/null 2>&1; then
    echo "All Brewfile dependencies are installed."
  else
    brew bundle install --file="$REPO_ROOT/Brewfile"
  fi
fi

command -v uv >/dev/null 2>&1 || die "uv not found. Run without --skip-brew or install uv: brew install uv"

step "Python environment (uv, Python $(cat .python-version))"
uv sync --locked

step "Android SDK packages, licenses, and AVD (configs/android/lab.yaml)"
uv run no-id-lab-android setup

step "Done"
echo "Start the emulator:   scripts/start_android_emulator.sh [--headless]"
echo "Validate the lab:     scripts/validate_android_lab.sh"
