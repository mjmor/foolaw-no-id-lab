# No-ID Lab

No-ID Lab is the investigation repository for **Team No ID** in the Tech Impact Lab / Foo Law Lab. The project partners with the Colorado and Connecticut state attorneys general to study age signals, minors' engagement mechanisms, and parental-control configurations across apps.

## Current state

This repository is in its bootstrap phase. It currently contains:

- Approved architecture and implementation plan
- Research plan and evidence model
- Automation-options assessment
- Repository validation tests
- Git repository setup

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
- `docs/superpowers/`: approved design and implementation plan
- `tests/`: repository validation tests

## Validate the repository

```bash
uv run pytest
```

## Ethics

This project uses synthetic personas and controlled test accounts. It does not collect or expose data from real minors, and it does not build mechanisms to circumvent age gates, authentication, parental controls, or app security.
