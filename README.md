# No-ID Lab

No-ID Lab is the investigation repository for **Team No ID** in the Tech Impact Lab / Foo Law Lab. The project partners with the Colorado and Connecticut state attorneys general to study age signals, minors' engagement mechanisms, and parental-control configurations across apps.

## Current state

This repository is in its bootstrap phase. It currently contains:

- Approved architecture and implementation plan
- Research plan and evidence model
- Automation-options assessment
- Repository validation tests
- Git repository setup
- A reproducible Android emulator lab for macOS (see [docs/android-emulator-lab.md](docs/android-emulator-lab.md))

## Investigation scope

- YouTube
- Instagram
- Facebook
- Snapchat
- TikTok
- Kick

## Research focus

- Age and minor-status signals
- Push notifications
- Recommended kid-friendly settings
- Default content filters
- Algorithmically surfaced content and delivery interfaces
- Parental notifications
- Contact attempts from outside the minor's network
- Variation by time of day and parental-control configuration

## Repository layout

- `AGENTS.md`: project instructions for agents
- `CLAUDE.md`: pointer to project agent instructions
- `docs/research-plan.md`: investigation plan and app matrix
- `docs/automation-options.md`: local automation assessment
- `docs/evidence-schema.md`: proposed evidence model
- `docs/android-emulator-lab.md`: Android emulator lab setup, operation, and troubleshooting
- `docs/superpowers/`: approved design and implementation plan
- `Brewfile`: macOS system dependencies (uv, openjdk@21, Android command-line tools)
- `configs/android/lab.yaml`: pinned Android API level, system image, device profile, and AVD
- `scripts/`: Android lab entry points (setup, start, stop, validate)
- `src/no_id_lab/android/`: SDK, AVD, emulator lifecycle, boot detection, and automation hooks
- `tests/`: repository, unit, and integration tests

## Android emulator lab

Requires macOS and [Homebrew](https://brew.sh). Everything else is installed by the setup script. Python comes from `uv` (pinned in `.python-version`), and the Android SDK and AVD live in the gitignored `.android-lab/` directory.

```bash
scripts/setup_macos.sh                         # idempotent: Brewfile, uv sync, SDK (android CLI), AVD
scripts/start_android_emulator.sh [--headless] # start and wait for boot
scripts/validate_android_lab.sh                # boot, verify adb, capture properties + screenshot, stop
scripts/stop_android_emulator.sh
```

See [docs/android-emulator-lab.md](docs/android-emulator-lab.md) for full instructions and troubleshooting.

## Validate the repository

```bash
uv sync
uv run pytest                  # unit tests
uv run pytest -m integration   # Android emulator integration tests (after setup)
```

## Ethics

This project uses synthetic personas and controlled test accounts. It does not collect or expose data from real minors, and it does not build mechanisms to circumvent age gates, authentication, parental controls, or app security.
