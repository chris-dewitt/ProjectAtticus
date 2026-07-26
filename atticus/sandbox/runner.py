"""Bounded local sandbox for Python snippets and allowlisted shell commands.

Network is denied by construction for the Python path (no sockets imported in
the child). Shell path only runs an allowlist with timeout and cwd confinement.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atticus.core.errors import AtticusError
from atticus.core.telemetry import get_telemetry


class SandboxDenied(AtticusError):
    code = "sandbox_denied"
    status_code = 400


@dataclass(frozen=True)
class SandboxResult:
    kind: str
    status: str
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "meta": dict(self.meta),
        }


_BLOCKED_PYTHON_MODULES = frozenset(
    {
        "socket",
        "ssl",
        "http",
        "urllib",
        "requests",
        "httpx",
        "subprocess",
        "ctypes",
        "multiprocessing",
        "pathlib",
        "os",
        "sys",
        "shutil",
        "tempfile",
        "importlib",
    }
)

_SHELL_ALLOWLIST = frozenset({"python", "python3", "echo", "dir", "ls", "type", "cat"})


class SandboxRunner:
    """Execute short untrusted snippets with hard bounds."""

    def __init__(
        self,
        *,
        work_dir: Path | None = None,
        timeout_seconds: float = 5.0,
        max_output_bytes: int = 32_000,
        allow_shell: bool = False,
    ) -> None:
        self._work_dir = work_dir
        self._timeout = timeout_seconds
        self._max_output = max_output_bytes
        self._allow_shell = allow_shell

    def run_python(self, source: str) -> SandboxResult:
        code = source.strip()
        if not code:
            raise SandboxDenied("Python sandbox source must not be empty.")
        if len(code) > 20_000:
            raise SandboxDenied("Python sandbox source exceeds 20KB.")
        self._assert_python_safe(code)

        wrapper = textwrap.dedent(
            f"""
            import ast
            import builtins
            import json
            import math
            import statistics
            import sys

            SAFE_BUILTINS = {{
                k: getattr(builtins, k)
                for k in (
                    "abs", "all", "any", "bool", "dict", "enumerate", "float",
                    "int", "len", "list", "max", "min", "print", "range",
                    "repr", "round", "set", "sorted", "str", "sum", "tuple",
                    "zip",
                )
                if hasattr(builtins, k)
            }}

            def _blocked_import(name, *args, **kwargs):
                raise ImportError(f"import blocked in sandbox: {{name}}")

            SAFE_BUILTINS["__import__"] = _blocked_import
            globals_dict = {{"__builtins__": SAFE_BUILTINS, "math": math, "statistics": statistics}}
            source = {code!r}
            tree = ast.parse(source, mode="exec")
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    raise SystemExit("import statements are blocked")
            exec(compile(tree, "<sandbox>", "exec"), globals_dict, {{}})
            """
        )

        return self._run_subprocess(
            kind="python",
            argv=[sys.executable, "-c", wrapper],
            meta={"chars": len(code)},
        )

    def run_shell(self, command: str) -> SandboxResult:
        if not self._allow_shell:
            raise SandboxDenied("Shell sandbox is disabled by configuration.")
        cmd = command.strip()
        if not cmd:
            raise SandboxDenied("Shell command must not be empty.")
        if len(cmd) > 500:
            raise SandboxDenied("Shell command exceeds 500 characters.")
        if any(ch in cmd for ch in (";", "|", "&", ">", "<", "`", "$", "\n")):
            raise SandboxDenied("Shell metacharacters are not allowed in sandbox.")
        parts = cmd.split()
        exe = parts[0].lower()
        if exe not in _SHELL_ALLOWLIST:
            raise SandboxDenied(
                f"Shell executable not allowlisted: {exe}",
                safe_details={"allowed": sorted(_SHELL_ALLOWLIST)},
            )
        return self._run_subprocess(kind="shell", argv=parts, meta={"argv0": exe})

    def _assert_python_safe(self, source: str) -> None:
        try:
            tree = ast.parse(source, mode="exec")
        except SyntaxError as exc:
            raise SandboxDenied(f"Invalid Python: {exc.msg}") from exc
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".", 1)[0]
                    if root in _BLOCKED_PYTHON_MODULES:
                        raise SandboxDenied(f"Import blocked: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".", 1)[0]
                if root in _BLOCKED_PYTHON_MODULES:
                    raise SandboxDenied(f"Import blocked: {node.module}")
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id in {"__builtins__", "__import__", "builtins"}:
                    raise SandboxDenied("Access to builtins introspection is blocked.")

    def _run_subprocess(
        self,
        *,
        kind: str,
        argv: list[str],
        meta: dict[str, Any],
    ) -> SandboxResult:
        import time

        work = self._work_dir
        if work is None:
            work = Path(tempfile.mkdtemp(prefix="atticus-sandbox-"))
        else:
            work.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                argv,
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
                env={
                    "PATH": str(Path(sys.executable).parent),
                    "PYTHONPATH": "",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            duration = round((time.perf_counter() - started) * 1000, 3)
            stdout = (completed.stdout or "")[: self._max_output]
            stderr = (completed.stderr or "")[: self._max_output]
            status = "ok" if completed.returncode == 0 else "error"
            result = SandboxResult(
                kind=kind,
                status=status,
                stdout=stdout,
                stderr=stderr,
                exit_code=int(completed.returncode),
                duration_ms=duration,
                meta=meta,
            )
        except subprocess.TimeoutExpired as exc:
            duration = round((time.perf_counter() - started) * 1000, 3)
            get_telemetry().emit("sandbox.timeout", kind=kind, duration_ms=duration)
            raise SandboxDenied(
                f"Sandbox timed out after {self._timeout}s",
                code="sandbox_timeout",
                status_code=408,
                safe_details={"kind": kind, "timeout_seconds": self._timeout},
            ) from exc

        get_telemetry().emit(
            "sandbox.completed",
            kind=kind,
            status=result.status,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
        )
        return result
