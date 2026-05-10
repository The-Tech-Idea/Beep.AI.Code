"""File watcher service with configurable rules.

Monitors filesystem changes and triggers actions.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from beep.workspace.ignore import IgnoreMatcher

WATCH_EXEC_TIMEOUT_SECONDS = 30.0


@dataclass
class WatchRule:
    """A rule that triggers an action on file changes."""

    pattern: str
    command: str
    debounce: float = 1.0
    enabled: bool = True
    last_triggered: float = 0.0


@dataclass
class WatchEvent:
    """A triggered watch event."""

    file: Path
    rule: WatchRule
    event_type: str


class WatchRuleHandler(FileSystemEventHandler):
    """Handles file system events and triggers rules."""

    def __init__(
        self,
        root: Path,
        rules: list[WatchRule],
        callback: Callable[[WatchEvent], None] | None = None,
    ) -> None:
        self._root = root
        self._rules = rules
        self._callback = callback
        self._matcher = IgnoreMatcher(root)
        self._queue: asyncio.Queue[WatchEvent] | None = None

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self._matcher.is_ignored(path):
            return

        for rule in self._rules:
            if not rule.enabled:
                continue
            if not path.match(rule.pattern):
                continue

            now = time.time()
            if now - rule.last_triggered < rule.debounce:
                continue

            rule.last_triggered = now
            watch_event = WatchEvent(
                file=path,
                rule=rule,
                event_type=event.event_type,
            )

            if self._callback:
                try:
                    self._callback(watch_event)
                except Exception:
                    # Keep watcher loop alive even if a callback fails once.
                    continue


@dataclass
class WatcherService:
    """Manages file watching with rules."""

    root: Path
    rules: list[WatchRule] = field(default_factory=list)
    _observer: Observer | None = field(default=None, repr=False)
    _running: bool = False

    def add_rule(self, pattern: str, command: str, debounce: float = 1.0) -> str:
        """Add a watch rule. Returns rule ID."""
        rule = WatchRule(pattern=pattern, command=command, debounce=debounce)
        self.rules.append(rule)
        return f"{pattern} -> {command}"

    def remove_rule(self, index: int) -> bool:
        """Remove a rule by index."""
        if 0 <= index < len(self.rules):
            self.rules.pop(index)
            return True
        return False

    def list_rules(self) -> list[tuple[int, WatchRule]]:
        """List all rules with indices."""
        return list(enumerate(self.rules))

    def start(self, callback: Callable[[WatchEvent], None] | None = None) -> None:
        """Start watching."""
        if self._running:
            return

        handler = WatchRuleHandler(self.root, self.rules, callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.root), recursive=True)
        self._observer.start()
        self._running = True

    def stop(self) -> None:
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running


async def execute_watch_event(event: WatchEvent) -> str:
    """Execute the command for a watch event."""
    try:
        proc = await asyncio.create_subprocess_shell(
            event.rule.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(event.file.parent),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=WATCH_EXEC_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            try:
                proc.kill()
                await proc.communicate()
            except Exception:
                pass
            return f"Failed: command timed out after {WATCH_EXEC_TIMEOUT_SECONDS:.0f}s"
        output = stdout.decode("utf-8", errors="replace")
        error = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            return output[:500] if output else "OK"
        details = (error or output).strip()
        if details:
            return f"Failed: {details[:300]}"
        return f"Failed: command exited with code {proc.returncode}"
    except Exception as exc:
        return f"Error: {exc}"
