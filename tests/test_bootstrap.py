from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


def read(path: Path) -> str:
    assert path.is_file(), f"Missing required file: {path}"
    return path.read_text(encoding="utf-8")


def test_workspace_context_documents_exist():
    agents = read(WORKSPACE_ROOT / "AGENTS.md")
    claude = read(WORKSPACE_ROOT / "CLAUDE.md")

    assert "Team No ID" in agents
    assert "Colorado" in agents
    assert "Connecticut" in agents
    assert "Kick" in agents
    assert "AGENTS.md" in claude


def test_repository_is_initialized():
    assert (REPO_ROOT / ".git").is_dir()


def test_repository_context_documents_exist():
    agents = read(REPO_ROOT / "AGENTS.md")
    claude = read(REPO_ROOT / "CLAUDE.md")
    readme = read(REPO_ROOT / "README.md")

    assert "No-ID Lab" in agents
    assert "AGENTS.md" in claude
    assert "No-ID Lab" in readme


def test_gitignore_excludes_local_evidence_artifacts():
    ignored = read(REPO_ROOT / ".gitignore")

    assert "__pycache__/" in ignored
    assert ".pytest_cache/" in ignored
    assert "credentials/" in ignored
    assert "captures/" in ignored
    assert "*.pem" in ignored


def test_research_plan_covers_apps_and_observation_categories():
    research_plan = read(REPO_ROOT / "docs" / "research-plan.md")

    for app in ["YouTube", "Instagram", "Facebook", "Snapchat", "TikTok", "Kick"]:
        assert app in research_plan

    for category in [
        "age signals",
        "push notifications",
        "parental notifications",
        "content filters",
        "outside network",
        "time of day",
    ]:
        assert category.lower() in research_plan.lower()


def test_automation_options_recommend_hybrid_local_lab():
    automation_options = read(REPO_ROOT / "docs" / "automation-options.md")

    assert "Android" in automation_options
    assert "iOS" in automation_options
    assert "Recommended approach" in automation_options
    assert "physical iPhone" in automation_options
    assert "Android emulator" in automation_options


def test_evidence_schema_defines_required_fields():
    evidence_schema = read(REPO_ROOT / "docs" / "evidence-schema.md")

    for field in [
        "observation_id",
        "platform",
        "app",
        "persona",
        "parental_control_profile",
        "local_time",
        "age_signal",
        "engagement_mechanism",
        "notification",
        "evidence_artifact",
        "statute_hook",
    ]:
        assert field in evidence_schema


def test_design_and_implementation_plan_exist():
    design = read(REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-10-07-no-id-lab-design.md")
    plan = read(REPO_ROOT / "docs" / "superpowers" / "plans" / "2026-10-07-no-id-lab-bootstrap.md")

    assert "Goal" in design
    assert "Implementation Plan" in plan
