from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from atticus.core.errors import WorkspaceError


def _normalize(cmd: str) -> str:
    return " ".join(shlex.split(cmd.strip()))


def assert_safe_git_command(cmd: str) -> None:
    """Reject shell metacharacters and unknown git invocations."""
    if any(ch in cmd for ch in (";", "|", "&", "`", "$(")):
        raise WorkspaceError("Shell metacharacters are not allowed in git commands.")
    n = _normalize(cmd)
    parts = shlex.split(cmd.strip())
    if len(parts) < 2 or parts[0] != "git":
        raise WorkspaceError("Only git subcommands are allowed.")
    exact = frozenset(
        {
            "git status",
            "git status --porcelain",
            "git status -sb",
            "git diff",
            "git diff --stat",
            "git branch --show-current",
            "git log -1 --oneline",
        }
    )
    if n in exact:
        return
    if n.startswith("git diff --stat --"):
        return
    raise WorkspaceError(f"Git command not on allow-list: {n}")


def run_git(cmd: str, *, cwd: Path, timeout: int = 60) -> str:
    assert_safe_git_command(cmd)
    parts = shlex.split(cmd)
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
        raise WorkspaceError("git command timed out.") from exc
    except OSError as exc:
        raise WorkspaceError(f"Failed to run git: {exc}") from exc
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise WorkspaceError(f"git exited {proc.returncode}:\n{out.strip()}")
    return out.strip()
