"""Command execution with logging. The single place that touches subprocess."""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        self.result = result
        detail = (result.stderr or result.stdout).strip()[-2000:]
        super().__init__(f"Command failed ({result.returncode}): {' '.join(result.args)}\n{detail}")


class Runner(Protocol):
    def run(
        self,
        args: Sequence[str | os.PathLike],
        *,
        env: Mapping[str, str] | None = None,
        input: str | None = None,
        timeout: float | None = None,
        check: bool = True,
    ) -> CommandResult: ...

    def spawn(
        self,
        args: Sequence[str | os.PathLike],
        *,
        env: Mapping[str, str] | None = None,
        log_path: Path | None = None,
    ) -> int: ...


class SubprocessRunner:
    def run(self, args, *, env=None, input=None, timeout=None, check=True) -> CommandResult:
        argv = tuple(str(a) for a in args)
        log.debug("run: %s", " ".join(argv))
        try:
            proc = subprocess.run(
                argv,
                env=dict(env) if env is not None else None,
                input=input,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            result = CommandResult(argv, -1, _text(exc.stdout), f"timed out after {timeout}s")
            raise CommandError(result) from exc
        result = CommandResult(argv, proc.returncode, proc.stdout, proc.stderr)
        if check and proc.returncode != 0:
            raise CommandError(result)
        return result

    def spawn(self, args, *, env=None, log_path=None) -> int:
        argv = tuple(str(a) for a in args)
        log.info("spawn: %s", " ".join(argv))
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            out = open(log_path, "ab")
        else:
            out = subprocess.DEVNULL
        try:
            proc = subprocess.Popen(
                argv,
                env=dict(env) if env is not None else None,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        finally:
            if log_path is not None:
                out.close()
        return proc.pid


def _text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
