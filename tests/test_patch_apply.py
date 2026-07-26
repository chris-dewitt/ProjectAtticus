from __future__ import annotations

from pathlib import Path

import pytest

from atticus.core.errors import WorkspaceError
from atticus.services.patch_apply import plan_patch


def test_plan_patch_accepts_relative_under_root(tmp_path: Path) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("a\n", encoding="utf-8")
    diff = """\
--- a/hello.txt
+++ b/hello.txt
@@ -1 +1 @@
-a
+b
"""
    plan = plan_patch(diff, approved_roots=[tmp_path], cwd=tmp_path)
    assert plan.target_paths == (target.resolve(),)
    assert plan.hunk_count == 1


def test_plan_patch_rejects_parent_escape(tmp_path: Path) -> None:
    diff = """\
--- a/../secret.txt
+++ b/../secret.txt
@@ -1 +1 @@
-a
+b
"""
    with pytest.raises(WorkspaceError, match="Unsafe"):
        plan_patch(diff, approved_roots=[tmp_path], cwd=tmp_path)
