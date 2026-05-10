"""Models for coding standards, task types, and review."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    """Classification of the agent's current task."""

    BUG_FIX = "bug_fix"
    NEW_FEATURE = "new_feature"
    REFACTOR = "refactor"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    PROTOTYPE = "prototype"


class ArchitectureProfile(str, Enum):
    """Architecture profiles for standards selection."""

    SIMPLE_SCRIPT = "simple_script"
    CLEAN_ARCHITECTURE = "clean_architecture"
    DDD = "ddd"
    WEB_API = "web_api"
    CLI_APP = "cli_app"
    LIBRARY = "library"


@dataclass
class CodingStandard:
    """A specific coding standard or rule set."""

    name: str
    description: str
    rules: list[str]
    applies_to_languages: list[str] = field(default_factory=lambda: ["*"])
    applies_to_project_types: list[str] = field(default_factory=lambda: ["*"])
    priority: int = 100


@dataclass
class ReviewIssue:
    """An issue found during standards review."""

    severity: str
    file_path: str
    line: Optional[int] = None
    rule: str = ""
    message: str = ""
    suggested_fix: Optional[str] = None
