# No-ID Lab

## Mission

No-ID Lab supports **Team No ID**'s investigation for the Tech Impact Lab / Foo Law Lab partnership with the Colorado and Connecticut state attorneys general. The lab surveys age signals, minors' engagement mechanisms, and parental-control configurations across major apps to help assess whether current statutory definitions are sufficient.

## Evidence-first workflow

1. Define the observation and the exact app/persona/control profile.
2. Record the parental-control state before starting.
3. Capture the app state, notification, or recommendation being evaluated.
4. Save evidence with an observation ID and metadata.
5. Map the observation to a statute-relevant research question.
6. Keep raw evidence and derived analysis separate.

## Directory map

- `docs/`: research plan, automation options, evidence schema, and approved design
- `docs/superpowers/`: design specifications and implementation plans
- `configs/android/lab.yaml`: declarative Android emulator lab configuration
- `configs/`: future persona, app, and parental-control profiles
- `scripts/`: Android lab entry points (setup, start, stop, validate); future automation and analysis entry points
- `src/no_id_lab/android/`: Android SDK, AVD, emulator lifecycle, boot detection, and automation hooks
- `tests/`: repository validation, unit, and integration tests
- `Brewfile`: macOS system dependencies
- `.android-lab/` (gitignored): local Android SDK, AVDs, emulator logs, and validation artifacts

## Documentation standards

- Keep observations tied to a defined research question.
- Document the platform, app version, OS version, persona, and parental-control profile.
- Do not use vague phrases such as "more engaging" without defining the evidence.
- Keep raw evidence, derived summaries, and statutory interpretation separate.

## Testing

This repository pins Python 3.13.7 in `.python-version` and manages dependencies with `uv`.

```bash
uv sync
uv run pytest                  # unit tests
uv run pytest -m integration   # boots the real Android emulator; run scripts/setup_macos.sh first
```

The Android emulator lab is documented in `docs/android-emulator-lab.md`. Extend it with new modules that use `AndroidLab`, `Adb`, and `DeviceTarget` rather than editing the lifecycle modules.

Tests should validate repository structure, required documentation, and future data schemas.

## Safety and ethics

- Use only synthetic or approved test personas.
- Do not collect or expose data from real minors.
- Do not circumvent age gates, authentication, parental controls, or app security.
- Keep credentials, raw captures, and large media files out of Git.
- Coordinate evidence-handling and publication decisions with the project's legal and AG partners.

## Adding a new app or persona

1. Add the app or persona to `docs/research-plan.md`.
2. Define the relevant parental-control matrix entries.
3. Extend `docs/evidence-schema.md` if new observation fields are required.
4. Add or update a validation test.
5. Update the README if the project scope changes.

## Git hygiene

- Do not use `git add -A` or `git add .`
- Stage explicit paths only.
- Inspect the diff before committing.
- Ask before creating pull requests.
- Keep each pull request focused on one concern.
