"""Apply unified diffs under approved workspace roots only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from atticus.core.errors import WorkspaceError

_FILE_HEADER = re.compile(r"^\+\+\+ [ab]/(.+)$")


@dataclass(frozen=True)
class PatchPlan:
    target_paths: tuple[Path, ...]
    hunk_count: int


def parse_unified_diff_targets(diff_text: str) -> list[str]:
    targets: list[str] = []
    for line in diff_text.splitlines():
        m = _FILE_HEADER.match(line.rstrip("\n"))
        if not m:
            continue
        rel = m.group(1).strip()
        if rel == "/dev/null":
            continue
        targets.append(rel)
    return targets


def plan_patch(diff_text: str, *, approved_roots: list[Path], cwd: Path) -> PatchPlan:
    if not diff_text.strip():
        raise WorkspaceError("Patch is empty.")
    if "\x00" in diff_text:
        raise WorkspaceError("Binary patches are not supported.")
    rels = parse_unified_diff_targets(diff_text)
    if not rels:
        raise WorkspaceError("No +++ file targets found in unified diff.")
    resolved: list[Path] = []
    for rel in rels:
        # Reject absolute and parent escapes before resolve.
        p = Path(rel)
        if p.is_absolute() or ".." in p.parts:
            raise WorkspaceError(f"Unsafe patch path rejected: {rel}")
        abs_path = (cwd / p).resolve()
        if not any(_is_under(abs_path, root) for root in approved_roots):
            raise WorkspaceError(f"Patch target outside approved_paths: {abs_path}")
        resolved.append(abs_path)
    hunks = sum(1 for line in diff_text.splitlines() if line.startswith("@@ "))
    return PatchPlan(target_paths=tuple(resolved), hunk_count=hunks)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def apply_unified_diff(
    diff_text: str,
    *,
    cwd: Path,
    approved_roots: list[Path],
    dry_run: bool = False,
) -> str:
    """
    Apply a unified diff with ``patch -p1`` semantics via Python when possible.

    Uses the system ``patch`` command if available; otherwise raises a clear error
    after validating paths (so approval UX still works in dry-run planning).
    """
    plan = plan_patch(diff_text, approved_roots=approved_roots, cwd=cwd)
    summary = (
        f"targets={len(plan.target_paths)}, hunks={plan.hunk_count}: "
        + ", ".join(str(p) for p in plan.target_paths[:8])
    )
    if dry_run:
        return f"dry-run ok — {summary}"

    import shutil
    import subprocess
    import tempfile

    patch_bin = shutil.which("patch")
    if not patch_bin:
        raise WorkspaceError(
            "System 'patch' command not found. Install a patch utility, or apply changes with /file write."
        )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".diff", delete=False) as fh:
        fh.write(diff_text)
        diff_path = Path(fh.name)
    try:
        proc = subprocess.run(
            [patch_bin, "-p1", "--forward", "--reject-file=-", "-i", str(diff_path)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        diff_path.unlink(missing_ok=True)
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        raise WorkspaceError(f"patch failed ({proc.returncode}): {out or summary}")
    return out or f"applied — {summary}"
