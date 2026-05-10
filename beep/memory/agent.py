"""Within-session agent memory for discovered facts."""

from __future__ import annotations

import json
from pathlib import Path


class AgentMemory:
    """Stores facts discovered by the agent during a session.

    Written to `<workspace>/.beep/session_memory.json`.
    Cleared when a new session starts.
    """

    _SCHEMA_VERSION = 1

    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._path = workspace_root / ".beep" / "session_memory.json"
        self._facts: dict[str, str] = {}

    def load(self) -> None:
        """Load existing session memory from disk."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    self._facts = {}
                    return

                migrated = False
                if "schema_version" in data:
                    version = data.get("schema_version")
                    if version != self._SCHEMA_VERSION:
                        self._facts = {}
                        return
                    facts = data.get("facts")
                    if isinstance(facts, dict):
                        self._facts = {str(k): str(v) for k, v in facts.items()}
                    else:
                        self._facts = {}
                    return

                self._facts = {str(k): str(v) for k, v in data.items()}
                migrated = True
                if migrated:
                    self._save()
            except (json.JSONDecodeError, OSError):
                self._facts = {}

    def remember(self, key: str, value: str) -> None:
        """Store a fact by key."""
        self._facts[key] = value
        self._save()

    def forget(self, key: str) -> None:
        """Remove a fact by key."""
        self._facts.pop(key, None)
        self._save()

    def clear(self) -> None:
        """Remove all facts and delete the file."""
        self._facts = {}
        if self._path.exists():
            self._path.unlink(missing_ok=True)

    def get(self, key: str) -> str | None:
        """Retrieve a fact by key."""
        return self._facts.get(key)

    def all_facts(self) -> dict[str, str]:
        """Return a copy of all stored facts."""
        return dict(self._facts)

    def to_prompt_section(self) -> str:
        """Return a Markdown section suitable for injecting into a system prompt."""
        if not self._facts:
            return ""
        lines = ["## Session Memory"]
        for key, value in self._facts.items():
            lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": self._SCHEMA_VERSION,
                "facts": self._facts,
            }
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass
