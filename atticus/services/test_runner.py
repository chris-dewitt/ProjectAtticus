"""Allow-listed test command runner (no arbitrary shell)."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from atticus.core.errors import WorkspaceError


def assert_safe_test_command(cmd: str) -> list[str]:
    if any(ch in cmd for ch in (";", "|", "&", "`", "$(", ">", "<", "\n")):
        raise WorkspaceError("Shell metacharacters are not allowed in test commands.")
    parts = shlex.split(cmd.strip())
    if not parts:
        raise WorkspaceError("Empty test command.")
    # Allowed forms:
    #   pytest ...
    #   python -m pytest ...
    #   python3 -m pytest ...
    if parts[0] in {"pytest", "py.test"}:
        return parts
    if parts[0] in {"python", "python3"} and len(parts) >= 3 and parts[1] == "-m" and parts[2] == "pytest":
        return parts
    raise WorkspaceError(
        "Only pytest invocations are allow-listed "
        "(pytest … or python -m pytest …)."
    )


def run_tests(cmd: str, *, cwd: Path, timeout: int = 120) -> str:
    parts = assert_safe_test_command(cmd)
    env = os.environ.copy()
    try:
        proc = subprocess.run(
            parts,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorkspaceError("test command timed out.") from exc
    except OSError as exc:
        raise WorkspaceError(f"Failed to run tests: {exc}") from exc
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    header = f"exit={proc.returncode}"
    return f"{header}\n{out}".strip()
