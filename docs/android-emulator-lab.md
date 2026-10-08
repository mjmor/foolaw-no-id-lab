# Android Emulator Lab

This document explains how to build the No-ID Lab Android emulator lab from scratch on any supported Mac. The lab gives later phases (app installation, UI automation, evidence capture) a reproducible device. It does not install or automate target apps.

Everything the lab needs is declared in three places:

| What | Where | Managed by |
|---|---|---|
| macOS tools: `uv`, `openjdk@21`, Android command-line tools | `Brewfile` | Homebrew (`brew bundle`) |
| Python 3.13.7 and Python dependencies | `.python-version`, `pyproject.toml`, `uv.lock` | `uv` |
| Android API level, system image, device profile, AVD, emulator flags, timeouts | `configs/android/lab.yaml` | `uv run no-id-lab-android setup` |

The SDK, AVD, logs, and validation artifacts are written to `.android-lab/` inside the repository. That directory is gitignored. The lab does not use `~/Library/Android`, an Android Studio install, or the system Python. Android tooling state (AVDs, emulator settings, `android` CLI cache, adb keys) goes to `.android-lab/user-home` through `ANDROID_USER_HOME`. Android tools run *outside* the lab scripts, without that variable, fall back to `~/.android`.

## 1. Prerequisites

- macOS 13 or newer on Apple Silicon (arm64) or Intel (x86_64). The setup script detects the host architecture and picks the matching system image: `arm64-v8a` on Apple Silicon, `x86_64` on Intel.
- Hardware virtualization. Apple Silicon always has it. On Intel Macs, the emulator uses Hypervisor.framework, which is built into macOS. Nested VMs (for example, a macOS VM in the cloud) usually do **not** support it.
- About 10 GB of free disk space: roughly 1.5 GB for the SDK packages, 8 GB of AVD data partition (allocated as it is used), plus logs.
- 8 GB of RAM or more. The AVD gets 4 GB (`avd.hardware.hw.ramSize`).
- [Homebrew](https://brew.sh). It is the only tool you install by hand, because its installer asks for an administrator password:

  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- A clone of this repository.

You do not need Android Studio, a system Java, or a system Python.

## 2. First-time installation

From the repository root:

```bash
scripts/setup_macos.sh
```

The script is idempotent. Run it again any time, for example after changing `configs/android/lab.yaml` or pulling new changes. Each run:

1. Installs any Brewfile dependencies that are missing (`brew bundle`).
2. Runs `uv sync --locked` to create `.venv` from `uv.lock` with Python 3.13.7.
3. Runs `uv run no-id-lab-android setup`, which:
   - Uses the `android` CLI (`android sdk install`) to install the pinned packages into `.android-lab/sdk`: `cmdline-tools/<version>`, `platform-tools`, `emulator`, and `system-images/android-<api>/<tag>/<abi>`. The first run uses the Homebrew copy of `android`. Later runs use the SDK's own pinned copy. Packages that are already installed (per `android sdk list`) are skipped. The CLI accepts the SDK licence terms without prompting, and the lab always passes `--no-metrics` so no usage data is sent to Google.
   - Creates the AVD with `avdmanager`. (`android emulator create` only accepts generic profiles such as `medium_phone` and always picks the newest image, so it cannot express the pinned API level, image, device, and AVD name.)
   - Brings an existing AVD back in line with the config (see section 4).
   - Ends with `doctor`, which prints every tool path and exits non-zero if anything is missing.

If Homebrew packages are managed some other way, for example on a machine without admin rights, `scripts/setup_macos.sh --skip-brew` skips step 1.

The first run downloads about 1.5 GB. Later runs finish in seconds.

## 3. Environment setup

The lab scripts set their own environment, so you do not need to export anything to use them. Each command builds its environment from `configs/android/lab.yaml`:

| Variable | Value |
|---|---|
| `ANDROID_HOME`, `ANDROID_SDK_ROOT` | `<lab_home>/sdk` |
| `ANDROID_USER_HOME`, `ANDROID_EMULATOR_HOME` | `<lab_home>/user-home` |
| `ANDROID_AVD_HOME` | `<lab_home>/user-home/avd` |
| `JAVA_HOME` | Homebrew `openjdk@21`, otherwise an existing `JAVA_HOME` that actually contains `bin/java` |
| `PATH` | Prefixed with `platform-tools`, `emulator`, `cmdline-tools/<version>/bin`, and `$JAVA_HOME/bin` |

A stale `JAVA_HOME` that points at a directory without Java is ignored. So is a deprecated `ANDROID_SDK_HOME`.

To use `adb`, `emulator`, `avdmanager`, or `android` directly in your shell with the same settings:

```bash
eval "$(uv run no-id-lab-android env)"
adb devices
```

Optional overrides:

| Variable | Effect |
|---|---|
| `NO_ID_LAB_ANDROID_LAB_HOME` | Put `.android-lab` somewhere else, for example on an external disk. |
| `NO_ID_LAB_ANDROID_CONFIG` | Use a different lab config file. |
| `ANDROID_HOME` | Used only when `sdk.path_policy: env`, to reuse an existing SDK instead of the project-local one. |

## 4. How to create or update the AVD

The AVD is defined in `configs/android/lab.yaml`:

```yaml
api_level: 35
system_image:
  tag: google_apis_playstore   # google_apis_playstore | google_apis | default
  architecture: auto        # auto | arm64-v8a | x86_64
device_profile: pixel_7
avd_name: no-id-lab-api35-play
avd:
  hardware:
    hw.ramSize: "4096"
    ...
```

To create or update the AVD, edit the file and rerun:

```bash
scripts/setup_macos.sh          # or: uv run no-id-lab-android setup
```

`setup` compares the existing AVD with the config:

- **Created**: no AVD with this name exists yet.
- **Recreated**: the system image, ABI, tag, or device profile changed. The AVD is rebuilt with `avdmanager create avd --force`, which **erases its user data**.
- **Updated**: only `avd.hardware` values changed. They are rewritten in the AVD's `config.ini`, and user data is kept.
- **Unchanged**: nothing to do.

To check the AVD without changing anything, run `uv run no-id-lab-android doctor`.

The image is the **Google Play** variant (`google_apis_playstore`), which includes the Play Store and Google Play services so apps can be installed from Google Play. `avd.hardware` sets `PlayStore.enabled: "true"`, matching what Android Studio does for Play images. Play images are production builds: `adb root` is not available.

To change the image tag or API level, also change `avd_name`, so the old and new AVDs can coexist. Then rerun setup. No code changes are needed. Setup does not delete old AVDs or images. Remove them with `android emulator remove <name>` and `android sdk remove <package>` (after `eval "$(uv run no-id-lab-android env)"`).

Note that the Google Play image ships some Google apps as preinstalled system apps, including **YouTube**, which is one of the in-scope apps. This phase never launches, signs into, or automates them. Later phases should record the preinstalled app version (`adb shell dumpsys package com.google.android.youtube | grep versionName`) as part of observation metadata.

## 5. How to start the emulator in normal mode

```bash
scripts/start_android_emulator.sh            # or: --window
```

This opens the emulator window and blocks until Android has fully booted. Then it prints `emulator-5554 booted`. The emulator keeps running in the background after the command returns, and its output goes to `.android-lab/logs/emulator-no-id-lab-api35-play.log`.

`emulator.boot_mode: cold` (the default) boots from scratch every time and does not save a snapshot on exit, so each session starts from the same device state. User data, such as test accounts added in later phases, is kept. Set `boot_mode: quick` to use quick-boot snapshots instead.

Add `--no-wait` to return right after launch, and use `uv run no-id-lab-android wait-boot` later. Running `start` again while the emulator is up is safe: it reports `already running`.

## 6. How to start the emulator headlessly

```bash
scripts/start_android_emulator.sh --headless
```

Headless mode adds `-no-window -no-audio -no-boot-anim` and uses software rendering (`emulator.headless_gpu: swiftshader_indirect`). Set `headless: true` in `lab.yaml` to make headless the default. `--window` and `--headless` always override the config.

## 7. How to verify that the emulator is ready

The emulator counts as booted only when all four of these are true:

1. `adb devices` lists `emulator-5554` in state `device`.
2. `getprop sys.boot_completed` returns `1`.
3. `pm path android` answers, which means the package manager is up.
4. `dumpsys window displays` shows a window with input focus (`mCurrentFocus` is not `null`).

Condition 4 matters. Right after `sys.boot_completed` flips, a first-boot setup activity is still running and nothing has focus, so screenshots come out black and UI automation would have nothing to drive. The launcher usually takes focus a few seconds later.

To check this:

```bash
uv run no-id-lab-android status      # JSON, exit 0 if booted, 3 if not
uv run no-id-lab-android wait-boot   # blocks until booted (timeouts.boot_seconds)
```

For a full end-to-end integration check:

```bash
scripts/validate_android_lab.sh               # headless by default; --window to watch
```

This command:

1. Runs `doctor`.
2. Starts the emulator if it is not already running.
3. Waits for boot.
4. Confirms `adb` reports the device.
5. Checks that the API level and ABI match the config.
6. Writes `device-properties.json` and `screenshot.png` to `.android-lab/artifacts/validation/<UTC timestamp>/`.
7. Stops the emulator, but only if the check started it.
8. Prints `Android lab validation passed`.

Use `--keep-running` to leave the emulator up afterwards.

Validation artifacts are lab diagnostics, not research evidence, and they stay out of Git.

## 8. How to stop the emulator

```bash
scripts/stop_android_emulator.sh
```

This sends `adb emu kill` and waits for the device and the emulator process to go away (`timeouts.stop_seconds`). If the emulator does not respond, the command sends SIGTERM to the emulator's process group. The pid comes from `.android-lab/run/`, and the process is checked to be an emulator before it is signalled. Running `stop` when nothing is running is a no-op.

## 9. How to run the automated tests

```bash
uv run pytest                    # unit tests; no SDK or emulator required
uv run pytest -m integration     # real SDK + emulator; requires setup to have run
```

Unit tests cover configuration parsing and validation, architecture detection, SDK path policy and environment, tool discovery, `android sdk` package diffing and invocation, AVD create, update, and drift detection, emulator command construction, start and stop wiring, boot detection, the validation flow, the Appium capability hook, script wiring, and this document. They use a fake command runner and never touch the real SDK.

Integration tests (marker `integration`) check that every tool is discoverable, the SDK paths are configured, the AVD matches the config, and that a headless emulator boots, is listed by `adb devices`, reports the pinned API level, produces a screenshot, and stops. Stop any running lab emulator before you run them.

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `error: No Java runtime found` | Run `brew bundle --file=Brewfile`. A stale `JAVA_HOME` is ignored automatically. |
| ``The `android` CLI was not found`` | The Homebrew cask `android-commandlinetools` is missing. Rerun `scripts/setup_macos.sh`. |
| `Downloading Android CLI... Unpacking embedded installation...` on the first call | Normal. The `android` binary unpacks itself into `<ANDROID_USER_HOME>/cli` once. |
| Validation screenshot is black | The UI was not ready yet. Readiness now waits for a focused window (section 7). If it still happens, check `adb shell dumpsys window displays \| grep mCurrentFocus`. |
| `android sdk install` fails to download | Network or proxy problem. The packages come from `dl.google.com`. Run `android -v --sdk="$ANDROID_HOME" sdk install <package>` (after `eval "$(uv run no-id-lab-android env)"`) for details. |
| `AVD '…' does not exist` | Run `scripts/setup_macos.sh`. |
| `AVD drift: …` warning on start | `lab.yaml` changed since the AVD was created. Rerun setup to converge. |
| `… is already running; stop it first` or port conflict | Another emulator is on console port 5554. Stop it, or change `emulator.console_port` (an even number from 5554 to 5682). |
| `did not finish booting within …s` | Look at the log tail in the error and `.android-lab/logs/`. Raise `timeouts.boot_seconds` on slower Macs. Close other VMs, such as Docker, to free RAM. |
| Emulator exits right away with HVF or hypervisor errors | Hardware virtualization is unavailable, which happens in nested VMs. Use a physical Mac. |
| Window is black or GPU errors in windowed mode | Set `emulator.gpu: swiftshader_indirect` in `lab.yaml`. |
| `adb` shows `unauthorized` or `offline` | Run `adb kill-server` (after `eval "$(uv run no-id-lab-android env)"`) and start again. Keys live in `.android-lab/user-home`. |
| Start over completely | Stop the emulator, `rm -rf .android-lab`, then rerun `scripts/setup_macos.sh`. |
| Sandbox or "Operation not permitted" errors when run by a coding agent | The emulator, Homebrew, and `android sdk` downloads need access outside the repository and the network. Run them outside the agent sandbox. |

## Code layout and extension points

`src/no_id_lab/android/` separates responsibilities so later phases can build on it without changing the core:

| Module | Responsibility |
|---|---|
| `config.py` | Loads and validates `lab.yaml`, resolves the host ABI, and builds SDK package names. |
| `paths.py` | Lab directory layout, SDK path policy, Java discovery, and the tool environment. |
| `runner.py` | All subprocess execution and logging. Tests replace it with a fake. |
| `sdk.py` | Tool discovery, `android` CLI bootstrap, and installing only missing SDK packages (`android sdk list/install`). |
| `avd.py` | AVD create, recreate, and update, plus drift validation against the config. |
| `adb.py` | `adb` wrapper: devices, shell, getprop, screenshot, `emu kill`. |
| `boot.py` | Boot-state detection and waiting. |
| `emulator.py` | Emulator process lifecycle: start detached, stop, pid and log files. |
| `lab.py` | `AndroidLab` facade that composes the modules (setup, start, stop, status, validate). |
| `automation.py` | `DeviceTarget` and UiAutomator2/Appium capabilities for the lab emulator. Adds no Appium dependency yet. |
| `cli.py` | The `no-id-lab-android` command used by the `scripts/` wrappers. |

Later phases should add app installation and evidence capture as new modules that use `AndroidLab`, `Adb`, and `DeviceTarget`. They should not put that logic into the lifecycle modules. Raw evidence belongs outside Git, as described in the research plan.
