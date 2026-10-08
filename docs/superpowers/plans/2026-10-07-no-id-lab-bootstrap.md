# No-ID Lab Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the No-ID Lab repository and document the approved investigation and automation approach.

**Architecture:** Create a documentation-first repository with workspace and repository agent instructions, a research plan, an automation-options assessment, an evidence schema, and validation tests. Keep the repository separate from raw evidence artifacts.

**Tech Stack:** Git, Markdown, Python, and pytest.

**Spec:** `docs/superpowers/specs/2026-10-07-no-id-lab-design.md`

## Global Constraints

- Use synthetic personas and controlled test accounts only.
- Do not collect data from real minors.
- Do not circumvent age gates, authentication, parental controls, or app security.
- Keep raw evidence outside Git.
- Do not use `git add -A` or `git add .`
- Stage explicit paths only.

## Review Focus

- Repository structure is valid.
- Required workspace and repo instructions exist.
- Research plan covers all target apps and observation categories.
- Automation recommendation explains Android and iOS tradeoffs.
- Evidence schema records platform, persona, control state, time, mechanism, and statute hook.

## Tasks

### Task 1: Workspace context

**Files:**

- Create: `/Users/max/Projects/foolawlab/AGENTS.md`
- Create: `/Users/max/Projects/foolawlab/CLAUDE.md`

**Interfaces:**

- Produces: workspace-level context for Team No ID, target apps, research scope, ethics, and Git rules.

- [ ] Create `AGENTS.md` with workspace purpose, scope, ethics, and workflow.
- [ ] Create `CLAUDE.md` pointing to `AGENTS.md`.

### Task 2: Repository bootstrap

**Files:**

- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `README.md`
- Create: `.gitignore`
- Create: `configs/`
- Create: `scripts/`

**Interfaces:**

- Produces: repository structure, agent instructions, project overview, and ignored artifact paths.

- [ ] Initialize a Git repository on the `main` branch.
- [ ] Create repo-specific agent instructions and Claude pointer.
- [ ] Create README and `.gitignore`.
- [ ] Create placeholder directories for configs and scripts.

### Task 3: Research and automation documentation

**Files:**

- Create: `docs/research-plan.md`
- Create: `docs/automation-options.md`
- Create: `docs/evidence-schema.md`
- Create: `docs/superpowers/specs/2026-10-07-no-id-lab-design.md`
- Create: `docs/superpowers/plans/2026-10-07-no-id-lab-bootstrap.md`

**Interfaces:**

- Produces: approved design, research plan, automation recommendation, evidence schema, and implementation plan.

- [ ] Document the research questions, apps, personas, control profiles, and evidence categories.
- [ ] Document the hybrid Android emulator plus physical iPhone approach.
- [ ] Define the evidence schema and storage model.
- [ ] Add the approved design and implementation plan.

### Task 4: Validation

**Files:**

- Create: `tests/test_bootstrap.py`

**Interfaces:**

- Consumes: all repository and workspace documentation files.
- Produces: validation that the repository is initialized and required documentation exists.

- [ ] Write tests that validate workspace and repository instructions.
- [ ] Run tests and confirm they initially fail.
- [ ] Create or update the documentation required by the tests.
- [ ] Run tests and confirm they pass.

### Task 5: Git commit

**Files:**

- Stage explicit repository files and directories.

**Interfaces:**

- Consumes: all files created by Tasks 1–4.
- Produces: initial local Git commit on `main`.

- [ ] Run `git status --porcelain=v1`.
- [ ] Stage explicit paths.
- [ ] Inspect the staged diff.
- [ ] Commit with: `Bootstrap No-ID Lab investigation repository`
- [ ] Confirm the repository is clean after the commit.

## Follow-up plans

- Android emulator lab: `docs/superpowers/plans/2026-10-07-android-emulator-lab.md` (operator guide: `docs/android-emulator-lab.md`)
