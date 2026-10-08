# Android App Install and Launch Recording Plan

**Goal:** Demonstrate automation that installs every in-scope app on the lab emulator and records the screen while each app opens.

**Architecture:** New modules sit on top of the existing lab (`AndroidLab`, `Adb`) without changing the emulator lifecycle:

- `configs/android/apps.yaml` holds the app catalog.
- `ui.py` handles `uiautomator` dump parsing and taps.
- `playstore.py` drives the Play Store listing to install apps.
- `recording.py` records each launch with the emulator's host-side recorder and writes manifests aligned with the evidence schema.
- `apps_cli.py` provides the `no-id-lab-apps` command, with two script wrappers.

**Operator documentation:** `docs/android-app-automation.md`

## Constraints

- Play Store sign-in is a manual, one-time step with the lab's controlled adult test account. No credentials in code or Git.
- No in-app sign-in, account creation, prompt answering, or parental-control changes.
- Raw captures go to the gitignored `captures/` folder (or `NO_ID_LAB_CAPTURES_DIR`).

## Tasks

- [x] App catalog with Play-verified package names, and validation tests
- [x] `uiautomator` UI helper and tests
- [x] Play Store installer: skips installed apps, detects the signed-out state, saves diagnostics, handles timeouts; tests
- [x] Launch recorder and manifests; tests, plus an integration test with the preinstalled YouTube
- [x] Switch from in-guest `screenrecord` (black or stale frames on this emulator) to `adb emu screenrecord`
- [x] `no-id-lab-apps` CLI, `scripts/install_android_apps.sh`, `scripts/record_android_apps.sh`
- [x] Documentation and README
- [ ] Run the Play Store install end to end after the test account is signed in on the emulator (blocked on that account)
