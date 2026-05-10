"""Pre/post command hooks.

Allows running custom commands before/after operations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


from beep.utils.console import get_console

HOOKS_FILE = Path.home() / ".beepai" / "hooks.json"


@dataclass
class Hook:
    """A command hook."""

    event: str
    command: str
    enabled: bool = True


@dataclass
class HookConfig:
    """Hook configuration."""

    hooks: list[Hook] = field(default_factory=list)

    def add(self, event: str, command: str) -> None:
        self.hooks.append(Hook(event=event, command=command))

    def remove(self, index: int) -> bool:
        if 0 <= index < len(self.hooks):
            self.hooks.pop(index)
            return True
        return False

    def toggle(self, index: int) -> bool:
        if 0 <= index < len(self.hooks):
            self.hooks[index].enabled = not self.hooks[index].enabled
            return True
        return False


def load_hooks() -> HookConfig:
    """Load hooks from file."""
    if not HOOKS_FILE.exists():
        return HookConfig()

    try:
        data = json.loads(HOOKS_FILE.read_text(encoding="utf-8"))
        hooks = [Hook(**h) for h in data.get("hooks", [])]
        return HookConfig(hooks=hooks)
    except (json.JSONDecodeError, OSError):
        return HookConfig()


def save_hooks(config: HookConfig) -> None:
    """Save hooks to file."""
    HOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "hooks": [
            {"event": h.event, "command": h.command, "enabled": h.enabled} for h in config.hooks
        ]
    }
    HOOKS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_hooks(event: str, config: HookConfig) -> list[str]:
    """Run hooks for an event. Returns output lines."""
    import subprocess

    outputs = []
    for hook in config.hooks:
        if hook.event == event and hook.enabled:
            try:
                result = subprocess.run(
                    hook.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.stdout:
                    outputs.append(result.stdout.strip())
                if result.stderr:
                    outputs.append(f"[dim]{result.stderr.strip()}[/dim]")
            except subprocess.TimeoutExpired:
                outputs.append(f"[red]Hook timed out: {hook.command}[/red]")
            except Exception as exc:
                outputs.append(f"[red]Hook error: {e}[/red]")
    return outputs
