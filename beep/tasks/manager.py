"""Background task manager for long-running operations."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    """Task status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """A background task."""

    id: str
    name: str
    command: str
    status: TaskStatus = TaskStatus.PENDING
    output: str = ""
    error: str = ""
    pid: int | None = None
    _process: asyncio.subprocess.Process | None = field(default=None, repr=False)


class TaskManager:
    """Manages background tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, BackgroundTask] = {}

    async def start(
        self,
        name: str,
        command: str,
        cwd: str | None = None,
    ) -> BackgroundTask:
        """Start a background task."""
        task = BackgroundTask(
            id=uuid.uuid4().hex[:8],
            name=name,
            command=command,
        )
        self._tasks[task.id] = task

        async def _run() -> None:
            task.status = TaskStatus.RUNNING
            try:
                task._process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                )
                task.pid = task._process.pid
                stdout, stderr = await task._process.communicate()
                task.output = stdout.decode("utf-8", errors="replace")
                task.error = stderr.decode("utf-8", errors="replace")
                task.status = (
                    TaskStatus.COMPLETED if task._process.returncode == 0 else TaskStatus.FAILED
                )
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                if task._process:
                    task._process.kill()
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)

        asyncio.create_task(_run())
        return task

    def get(self, task_id: str) -> BackgroundTask | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_all(self) -> list[BackgroundTask]:
        """List all tasks."""
        return list(self._tasks.values())

    def cancel_all(self) -> None:
        """Cancel all running tasks owned by this manager."""
        for task in self._tasks.values():
            if task._process and task.status == TaskStatus.RUNNING:
                task._process.kill()
                task.status = TaskStatus.CANCELLED

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self._tasks.get(task_id)
        if task and task._process and task.status == TaskStatus.RUNNING:
            task._process.kill()
            task.status = TaskStatus.CANCELLED
            return True
        return False
