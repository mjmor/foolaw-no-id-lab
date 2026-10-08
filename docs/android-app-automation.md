# Android App Automation

This guide covers the automation that installs the in-scope apps on the lab emulator and records the screen while each app launches. It builds on the emulator lab in [android-emulator-lab.md](android-emulator-lab.md). Set that up first.

| Command | What it does |
|---|---|
| `uv run no-id-lab-apps list` | Lists the in-scope apps. If the emulator is running, also shows whether each app is installed and its version. |
| `scripts/install_android_apps.sh [--app ID ...]` | Installs apps from the Google Play Store app on the emulator. |
| `scripts/record_android_apps.sh [--app ID ...]` | Records the emulator display while launching each installed app. |

The apps are listed in `configs/android/apps.yaml`: YouTube, YouTube Kids, Instagram, Facebook, Messenger, Snapchat, TikTok, and Kick. Each entry has an `id` (used with `--app`), a display name, and a Play Store package name. The package names were checked against `play.google.com` on 2026-10-07.

## Ethics and scope

- Sign in to the Play Store only with the lab's **controlled test account**: a dedicated adult Google account created for this lab. Never use a personal account, and never use an account that belongs to a real child.
- Which Google account is signed in can itself act as an age signal for the apps. Keep the install account separate from the synthetic persona accounts that later phases will use, and record which one was active.
- This automation does not sign in to any app, create accounts, change parental controls, or answer prompts. It does not circumvent age gates, authentication, parental controls, or app security.
- No data from minors is collected. Recordings show only what the lab emulator displays when an app opens with no in-app account.

## 1. One-time step: sign in to the Play Store

Installing from Google Play requires a signed-in Google account. This step is manual on purpose: credentials never pass through the scripts or the repository.

1. `scripts/start_android_emulator.sh --window`
2. In the emulator, open **Play Store**, tap **Sign in**, and sign in with the lab's controlled test account.
3. Finish or skip any optional Google setup screens.

The sign-in is stored in the AVD's user data. It survives emulator restarts, because cold boot keeps user data. It is lost if the AVD is recreated (see "Recreated" in [android-emulator-lab.md](android-emulator-lab.md#4-how-to-create-or-update-the-avd)).

## 2. Install the in-scope apps

```bash
scripts/install_android_apps.sh                    # all apps
scripts/install_android_apps.sh --app tiktok --app kick
```

The script starts the emulator if it is not running and leaves it running afterwards. For each app it:

1. Skips the app if it is already installed. This includes YouTube, which comes preinstalled on the Google Play system image.
2. Opens the app's Play Store page (`market://details?id=<package>`).
3. Finds the **Install** button with `uiautomator dump` and taps it.
4. Waits until `pm path <package>` reports the app (`install.timeout_seconds`, default 15 minutes).

Exit codes:

| Code | Meaning |
|---|---|
| 0 | Every requested app is installed. |
| 1 | At least one app failed. A UI dump and a screenshot are saved under `.android-lab/artifacts/install/<timestamp>/`. |
| 2 | The Play Store is not signed in. Do step 1, then rerun. Nothing was installed. |

Running the script again is safe: installed apps are skipped.

## 3. Record each app launching

```bash
scripts/record_android_apps.sh                      # all installed apps, 20 s each
scripts/record_android_apps.sh --app youtube --seconds 10 --headless
```

For each installed app, the recorder:

1. Force-stops the app and goes to the home screen, so every recording starts with a cold launch.
2. Starts the emulator's host-side recorder (`adb emu screenrecord start`).
3. Waits `recording.settle_seconds`, reads the device clock, and launches the app from its launcher entry.
4. Stops after `recording.seconds`, waits for the WebM file to be written, then force-stops the app again.

It never taps anything inside the app. First-run prompts, such as YouTube's "Allow YouTube to send you notifications?", stay on screen and are captured as they appear. Apps that are not installed are reported as `skipped-not-installed`.

If the recorder started the emulator, it stops it at the end unless `--keep-running` is given. The exit code is 1 if any recording failed.

### Why the emulator's host-side recorder

The in-guest `screenrecord` tool was unreliable on this emulator. One 20-second run produced only all-black frames, and another missed an app launch that the host-side recorder captured. `adb emu screenrecord` records exactly what the emulator display shows, writes WebM directly on the host, and works in headless mode. A future physical-device tier will need the in-guest `screenrecord` instead.

## Captures

Each run writes to `captures/android-emulator-<UTC timestamp>/`. The directory is gitignored. Set `NO_ID_LAB_CAPTURES_DIR` to write somewhere else, such as an encrypted external volume.

```text
captures/android-emulator-20261008T040440Z/
├── run.json          # run summary: device, and per-app status, video, manifest
├── youtube.webm      # raw recording
└── youtube.json      # capture manifest
```

The manifest uses the field names from [evidence-schema.md](evidence-schema.md):

- Filled in from the device: `platform`, `app`, `app_version`, `os_version`, `local_time` (device clock), `time_window`, `evidence_artifact`, and `sha256` (the video's hash, for integrity).
- Recording details: the `device` profile and the `recording` settings.
- Deliberately left `null`: `persona`, `parental_control_profile`, `parental_control_state`, `engagement_mechanism`, and `statute_hook`. This automation does not configure or interpret those.

A manifest is a capture record, not a reviewed observation. Turning captures into observations (persona, control state, statute mapping) is a later phase.

## Automated tests

```bash
uv run pytest                     # unit tests (fake device)
uv run pytest -m integration      # includes recording the preinstalled YouTube on the real emulator
```

Unit tests cover the app catalog and its validation, observation time windows, install-state detection, launch and close commands, `uiautomator` XML parsing and taps, the Play Store flow (already installed, install and wait, signed-out stop, missing Install button with diagnostics, timeout, continuing after a failure), the recorder's command order and manifest, and the CLI and script wiring.

The Play Store install flow has not been run end to end yet, because it needs the signed-in test account from step 1. Until then, its integration coverage is limited to detecting the signed-out state.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Install exits with code 2 ("Sign in to the Play Store…") | Do step 1. The emulator must be the lab AVD (`no-id-lab-api35-play`). |
| `failed  No Install button…` | Open the screenshot in `.android-lab/artifacts/install/<timestamp>/`. Common causes: the app isn't available in the account's country, the device is incompatible, or the listing shows "Install on more devices" only. |
| `failed  Install timed out` | The download is slow, or a Play Store dialog (payment setup, account verification) is waiting for input. Handle it in the emulator window and rerun. Raise `install.timeout_seconds` for slow networks. |
| `skipped-not-installed` during recording | Run the install script first. |
| `emulator recorder refused to start: KO…` | Another `adb emu screenrecord` is running. Run `adb emu screenrecord stop` (after `eval "$(uv run no-id-lab-android env)"`) and retry. |
| Recording shows a prompt instead of the app's feed | Expected. The automation never answers first-run prompts. |
| Large capture directories | Each 20 s recording is about 5–7 MB at the default `bit_rate: 4M`. Lower `recording.bit_rate` or `recording.seconds` in `apps.yaml`. |

## Code layout

| Module | Responsibility |
|---|---|
| `apps.py` | Loads `apps.yaml`; install-state, launch, and close helpers; research-plan time windows. |
| `ui.py` | Parses `uiautomator dump` output and taps nodes. A stopgap until the Appium/UiAutomator2 driver (`automation.DeviceTarget`) is in place. |
| `playstore.py` | `PlayStoreInstaller`: drives the Play Store listing; detects the signed-out state; diagnostics on failure. |
| `recording.py` | `AppRecorder`: launch recordings with the emulator's host-side recorder, plus manifests. |
| `apps_cli.py` | The `no-id-lab-apps` command used by the two scripts. |

These modules use the lab's existing `AndroidLab`, `Adb`, and configuration. The emulator lifecycle modules are unchanged.
