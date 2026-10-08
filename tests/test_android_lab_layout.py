import os
import subprocess

import pytest

from conftest import REPO_ROOT
from no_id_lab.android.cli import build_parser

SCRIPTS = {
    "setup_macos.sh": "setup",
    "start_android_emulator.sh": "start",
    "stop_android_emulator.sh": "stop",
    "validate_android_lab.sh": "validate",
}


@pytest.mark.parametrize(("script", "subcommand"), SCRIPTS.items())
def test_scripts_are_executable_valid_bash_and_delegate_to_cli(script, subcommand):
    path = REPO_ROOT / "scripts" / script

    assert path.is_file()
    assert os.access(path, os.X_OK)
    subprocess.run(["bash", "-n", str(path)], check=True)
    text = path.read_text()
    assert "no-id-lab-android" in text
    assert f" {subcommand}" in text
    assert "uv run" in text


def test_brewfile_declares_system_dependencies():
    brewfile = (REPO_ROOT / "Brewfile").read_text()

    assert 'brew "uv"' in brewfile
    assert 'brew "openjdk@21"' in brewfile
    assert 'cask "android-commandlinetools"' in brewfile


def test_gitignore_keeps_emulator_state_out_of_git():
    assert ".android-lab/" in (REPO_ROOT / ".gitignore").read_text()


@pytest.mark.parametrize(
    "argv",
    [
        ["doctor"],
        ["setup"],
        ["env"],
        ["start", "--headless"],
        ["start", "--window", "--no-wait"],
        ["wait-boot"],
        ["status"],
        ["stop"],
        ["validate", "--headless"],
    ],
)
def test_cli_exposes_lifecycle_commands(argv):
    args = build_parser().parse_args(argv)

    assert args.command == argv[0]


def test_android_lab_documentation_covers_required_topics():
    doc = (REPO_ROOT / "docs" / "android-emulator-lab.md").read_text().lower()

    for topic in [
        "prerequisites",
        "first-time installation",
        "environment setup",
        "create or update the avd",
        "start the emulator",
        "headless",
        "verify",
        "stop the emulator",
        "automated tests",
        "troubleshooting",
    ]:
        assert topic in doc, topic


def test_readme_points_to_android_lab_docs():
    readme = (REPO_ROOT / "README.md").read_text()

    assert "docs/android-emulator-lab.md" in readme
    assert "scripts/setup_macos.sh" in readme
