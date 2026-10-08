# Android Emulator Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a reproducible Android emulator lab on macOS that later phases can extend with app installation, UI automation, and evidence capture.

**Architecture:** System tools are declared in a `Brewfile`. Python is pinned with `uv`. The Android profile is declared in `configs/android/lab.yaml`. A small Python package (`src/no_id_lab/android/`) separates SDK management, AVD management, emulator lifecycle, boot detection, command execution, and the automation hook. Thin shell scripts call the `no-id-lab-android` CLI. All Android state lives in the gitignored, project-local `.android-lab/`.

**Tech Stack:** Homebrew, openjdk@21, Android command-line tools (`sdkmanager`, `avdmanager`), Android Emulator, `adb`, Python 3.13.7, `uv`, PyYAML, pytest.

**Operator documentation:** `docs/android-emulator-lab.md`

## Global Constraints

- Do not install or automate target social-media apps in this phase.
- Use synthetic personas and controlled test accounts only. Do not collect data from real minors.
- Do not circumvent age gates, authentication, parental controls, or app security.
- Keep the SDK, AVDs, logs, and screenshots out of Git (`.android-lab/`).
- Do not hard-code personal paths. Use project-relative paths and documented environment variables.
- Stage explicit paths only.

## Decisions

| Decision | Rationale |
|---|---|
| API 35, `google_apis`, `pixel_7` | Current, stable image available for both arm64-v8a and x86_64. Google Play services are present for later app behaviour. Switching to `google_apis_playstore` is a config change. |
| Project-local SDK and AVD home (`sdk.path_policy: project`) | Hermetic and reproducible. Does not depend on Android Studio or the user's home layout. `env` policy reuses an existing `$ANDROID_HOME`. |
| Homebrew `android-commandlinetools` only bootstraps `sdkmanager` | The SDK then installs its own pinned `cmdline-tools;23.0`, so tool versions come from `lab.yaml`, not the cask. |
| `openjdk@21` (keg-only formula) | No sudo or GUI installer. Discovered explicitly, so a stale `JAVA_HOME` cannot break setup. |
| Cold boot by default | Each session starts from the same device state. Quick boot is available. |
| Integration tests behind the `integration` marker | `uv run pytest` stays fast and runs anywhere. The emulator check is explicit. |

## Tasks

### Task 1: Tests first

- [x] Unit tests for config parsing and validation, ABI detection, SDK paths and environment, Java discovery, tool discovery, and `sdkmanager` behaviour (`tests/test_android_config.py`, `tests/test_android_sdk.py`).
- [x] Unit tests for AVD create, update, and drift, plus `config.ini` handling (`tests/test_android_avd.py`).
- [x] Unit tests for start command construction, start and stop wiring, boot detection, retries, and validation flow (`tests/test_android_emulator.py`).
- [x] Unit tests for the Appium capability hook, scripts, Brewfile, gitignore, CLI, and docs (`tests/test_android_automation.py`, `tests/test_android_lab_layout.py`).
- [x] Integration tests against the real SDK and emulator (`tests/test_android_integration.py`).
- [x] Confirm the tests fail before implementation.

### Task 2: Declarative configuration and dependency manifests

- [x] `configs/android/lab.yaml`
- [x] `Brewfile`
- [x] `pyproject.toml`: PyYAML, `uv_build` package, `no-id-lab-android` script, `integration` marker. `uv.lock` updated.

### Task 3: Python package `src/no_id_lab/android/`

- [x] `config.py`, `paths.py`, `runner.py`
- [x] `sdk.py`, `avd.py`
- [x] `adb.py`, `boot.py`, `emulator.py`
- [x] `lab.py` facade, `automation.py`, `cli.py`

### Task 4: Entry points

- [x] `scripts/setup_macos.sh`: idempotent; Brewfile, `uv sync --locked`, SDK, licenses, AVD
- [x] `scripts/start_android_emulator.sh`, `scripts/stop_android_emulator.sh`
- [x] `scripts/validate_android_lab.sh`: doctor, then boot, adb check, properties, screenshot, stop

### Task 5: Verification

- [x] `uv run pytest` passes.
- [x] `scripts/setup_macos.sh` runs twice. The second run installs nothing and reports the AVD `unchanged`.
- [x] `scripts/validate_android_lab.sh` passes.
- [x] `uv run pytest -m integration` passes.

### Task 6: Documentation and commit

- [x] `docs/android-emulator-lab.md`, `README.md`, `AGENTS.md`
- [x] Stage explicit paths, inspect the full diff, and commit.

## Next phase hand-off

- App installation: add a module (for example `src/no_id_lab/android/apps.py`) that uses `AndroidLab.adb`. For Play Store installs, switch `system_image.tag` to `google_apis_playstore` with a new `avd_name`.
- UI automation: add the Appium client as a dependency and build sessions from `DeviceTarget.uiautomator2_capabilities()`.
- Evidence capture: write raw captures outside Git, following `docs/evidence-schema.md`. Do not reuse `.android-lab/artifacts/validation`, which holds only lab diagnostics.
