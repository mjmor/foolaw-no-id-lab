from __future__ import annotations

from pathlib import Path

import pytest

from no_id_lab.android.runner import CommandError, CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_CONFIG = REPO_ROOT / "configs" / "android" / "lab.yaml"


class FakeRunner:
    """Records commands and replies with canned output keyed by a substring of the command line."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.spawned: list[dict] = []
        self._responses: list[tuple[str, list[CommandResult | Exception]]] = []
        self._hooks: list[tuple[str, object]] = []

    def hook(self, needle: str, fn) -> None:
        self._hooks.append((needle, fn))

    def on(self, needle: str, *outputs: str | Exception, returncode: int = 0) -> None:
        replies: list[CommandResult | Exception] = []
        for output in outputs or ("",):
            if isinstance(output, Exception):
                replies.append(output)
            else:
                replies.append(CommandResult(args=(), returncode=returncode, stdout=output, stderr=""))
        self._responses.append((needle, replies))

    def run(self, args, *, env=None, input=None, timeout=None, check=True):
        args = tuple(str(a) for a in args)
        self.calls.append({"args": args, "env": env, "input": input})
        line = " ".join(args)
        for needle, fn in self._hooks:
            if needle in line:
                fn(args)
        for needle, replies in self._responses:
            if needle in line:
                reply = replies.pop(0) if len(replies) > 1 else replies[0]
                if isinstance(reply, Exception):
                    raise reply
                result = CommandResult(args=args, returncode=reply.returncode, stdout=reply.stdout, stderr="")
                if check and result.returncode != 0:
                    raise CommandError(result)
                return result
        return CommandResult(args=args, returncode=0, stdout="", stderr="")

    def spawn(self, args, *, env=None, log_path=None):
        args = tuple(str(a) for a in args)
        self.spawned.append({"args": args, "env": env, "log_path": log_path})
        return 4242

    def lines(self) -> list[str]:
        return [" ".join(call["args"]) for call in self.calls]


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()
