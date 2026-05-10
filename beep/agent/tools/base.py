"""Base tool interface for agent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: str
    error: str | None = None
    is_error: bool = False


class BaseTool(ABC):
    """Base class for agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used in LLM function calling."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema parameters for the tool."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments."""

    @property
    def optional_params(self) -> list[str]:
        """Parameter keys that are optional.

        Override in subclasses to declare which parameters the LLM may omit.
        All parameters not listed here are treated as required.
        """
        return []

    @property
    def category(self) -> str:
        """Tool category for filtering.

        Derived from the tool name by default:
        - ``file_*``  → ``"file"``
        - ``shell``   → ``"exec"``
        - ``search``  → ``"search"``
        - ``git*``    → ``"git"``
        - ``context`` → ``"context"``
        - everything else → ``"misc"``
        """
        n = self.name
        if n.startswith("file_") or n == "glob_files":
            return "file"
        if n == "shell":
            return "exec"
        if n == "search":
            return "search"
        if n.startswith("git"):
            return "git"
        if n == "context":
            return "context"
        return "misc"

    @property
    def read_only_safe(self) -> bool:
        """Whether the tool is safe to expose in read-only agent mode.

        Tools that always mutate the workspace should override this property
        or rely on the conservative name-based default below. Tools like
        ``git`` remain available because their approval checks are
        subcommand-aware at execution time. External plugin and MCP tools
        should declare this explicitly instead of relying on the inherited
        default.
        """
        return self.name not in {"file_write", "file_edit", "single_edit", "shell"}

    def to_openai_tool(self) -> dict[str, Any]:
        """Convert to OpenAI tool definition."""
        optional = set(self.optional_params)
        required = [k for k in self.parameters if k not in optional]
        schema: dict[str, Any] = {
            "type": "object",
            "properties": self.parameters,
        }
        if required:
            schema["required"] = required
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }
