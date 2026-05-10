"""Phase-aware agent state for explicit loop control."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentPhase(str, Enum):
    UNDERSTAND = "understand"
    CONTEXT = "context"
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"
    REPAIR = "repair"
    FINAL = "final"


@dataclass
class AgentState:
    """Explicit state model for phase-aware agent control."""

    task: str
    phase: AgentPhase = AgentPhase.UNDERSTAND
    steps: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    changed_files: set[str] = field(default_factory=set)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    build_results: list[dict[str, Any]] = field(default_factory=list)
    max_iterations: int = 25
    iteration: int = 0
    editing_happened: bool = False
    validation_passed: bool | None = None

    def add_step(self, kind: str, data: dict[str, Any]) -> None:
        self.steps.append({"kind": kind, "data": data})

    def add_failure(self, failure: dict[str, Any]) -> None:
        self.failures.append(failure)

    def record_edit(self, file_path: str) -> None:
        self.changed_files.add(file_path)
        self.editing_happened = True

    def should_validate(self) -> bool:
        return self.editing_happened and self.phase != AgentPhase.FINAL

    def should_repair(self) -> bool:
        return self.validation_passed is False

    def force_replan(self) -> None:
        self.phase = AgentPhase.PLAN
        self.editing_happened = False
        self.validation_passed = None

    def advance(self) -> None:
        if self.should_repair():
            self.phase = AgentPhase.REPAIR
            self.validation_passed = None
        elif self.should_validate():
            self.phase = AgentPhase.VALIDATE
        elif self.phase == AgentPhase.VALIDATE and self.validation_passed:
            self.phase = AgentPhase.FINAL
        elif self.phase == AgentPhase.REPAIR:
            self.phase = AgentPhase.EXECUTE
