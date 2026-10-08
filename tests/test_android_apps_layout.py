import os
import subprocess

import pytest

from conftest import REPO_ROOT
from no_id_lab.android.apps_cli import build_parser

SCRIPTS = {
    "install_android_apps.sh": "install",
    "record_android_apps.sh": "record",
}


@pytest.mark.parametrize(("script", "subcommand"), SCRIPTS.items())
def test_app_scripts_are_executable_and_delegate_to_cli(script, subcommand):
    path = REPO_ROOT / "scripts" / script

    assert os.access(path, os.X_OK)
    subprocess.run(["bash", "-n", str(path)], check=True)
    text = path.read_text()
    assert f"uv run no-id-lab-apps {subcommand}" in text


@pytest.mark.parametrize(
    "argv",
    [
        ["list"],
        ["install"],
        ["install", "--app", "tiktok", "--app", "kick"],
        ["record"],
        ["record", "--app", "youtube", "--seconds", "10", "--headless", "--keep-running"],
    ],
)
def test_apps_cli_commands(argv):
    args = build_parser().parse_args(argv)

    assert args.command == argv[0]


def test_record_cli_collects_app_ids_and_overrides():
    args = build_parser().parse_args(["record", "--app", "youtube", "--app", "kick", "--seconds", "10"])

    assert args.apps == ["youtube", "kick"]
    assert args.seconds == 10


def test_captures_directory_is_gitignored():
    assert "captures/" in (REPO_ROOT / ".gitignore").read_text().splitlines()


def test_app_automation_documentation_covers_workflow():
    doc = (REPO_ROOT / "docs" / "android-app-automation.md").read_text().lower()

    for topic in ["sign in", "install", "record", "captures", "troubleshooting", "test account", "minors"]:
        assert topic in doc, topic
    assert "docs/android-app-automation.md" in (REPO_ROOT / "README.md").read_text()
