# No-ID Lab Design

## Goal

Create a reproducible investigation repository for Team No ID's study of age signals, minors' engagement mechanisms, and parental-control configurations across YouTube, Instagram, Facebook, Snapchat, TikTok, and Kick.

## Approved approach

Use a hybrid local automation model:

- Android emulator as the first automated tier
- Physical iPhone as the authoritative iOS tier
- Physical Android device as a later validation tier
- Structured evidence records with statute hooks
- Synthetic personas and controlled test accounts only

## Investigation architecture

1. Define personas, apps, and parental-control profiles in configuration files.
2. Run a scripted device harness that captures UI, notification, settings, and engagement state.
3. Store structured observation records outside the repository.
4. Generate per-app, per-platform, and per-control matrices.
5. Map each observation to the relevant Colorado or Connecticut statutory hook.

## Evidence model

Observations should include:

- Platform and app version
- Persona and parental-control state
- Local time and observation window
- Age or minor-status signal
- Engagement mechanism
- Notification, filter, or contact behavior
- Evidence artifact reference
- Statute hook

## Repository structure

- `configs/`: future persona, app, and control profiles
- `docs/`: research and implementation documentation
- `scripts/`: future automation and analysis entry points
- `tests/`: repository and schema validation

## Non-goals

- Do not collect data from real minors.
- Do not circumvent age gates, authentication, parental controls, or app security.
- Do not treat mobile web as the primary evidence source.
- Do not rely on iOS Simulator for statutory-facing evidence.

## Statutory mapping

The project should map observations to Colorado and Connecticut provisions concerning duty of care, engagement features, age signals, parental controls, and contact restrictions.

## Risks

- App behavior may differ between emulators and physical devices.
- Notification and parental-control behavior may require manual validation.
- Network capture may be blocked by TLS pinning.
- App updates can change settings and should be recorded per observation.
