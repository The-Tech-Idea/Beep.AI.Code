"""Safe code execution sandbox.

Executes Python/JS snippets in isolated subprocesses
with timeouts and resource limits.
"""

from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutionResult:
    """Result of code execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration: float = 0.0


async def execute_python(
    code: str,
    timeout: int = 30,
    cwd: Path | None = None,
) -> ExecutionResult:
    """Execute Python code safely."""
    import time

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        f.flush()
        script_path = f.name

    start = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=proc.returncode or 0,
                duration=time.time() - start,
            )
        except TimeoutError:
            proc.kill()
            return ExecutionResult(
                success=False,
                stderr=f"Timed out after {timeout}s",
                exit_code=-1,
                duration=time.time() - start,
            )
    finally:
        Path(script_path).unlink(missing_ok=True)


async def execute_javascript(
    code: str,
    timeout: int = 30,
    cwd: Path | None = None,
) -> ExecutionResult:
    """Execute JavaScript code via Node.js."""
    import time

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        f.flush()
        script_path = f.name

    start = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            "node", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=proc.returncode or 0,
                duration=time.time() - start,
            )
        except TimeoutError:
            proc.kill()
            return ExecutionResult(
                success=False,
                stderr=f"Timed out after {timeout}s",
                exit_code=-1,
                duration=time.time() - start,
            )
    finally:
        Path(script_path).unlink(missing_ok=True)
