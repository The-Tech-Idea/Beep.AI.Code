"""Typed streaming events for agent execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentEvent:
    """Base class for all agent streaming events."""

    type: str
    step: int = 0


@dataclass(frozen=True)
class NodeStartEvent(AgentEvent):
    """A graph node has started execution."""

    node: str = ""


@dataclass(frozen=True)
class NodeEndEvent(AgentEvent):
    """A graph node has finished execution."""

    node: str = ""
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolStartEvent(AgentEvent):
    """A tool call is about to execute."""

    tool: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResultEvent(AgentEvent):
    """A tool call has completed."""

    tool: str = ""
    output: str = ""
    success: bool = True


@dataclass(frozen=True)
class ResponseChunkEvent(AgentEvent):
    """A chunk of agent response text."""

    content: str = ""


@dataclass(frozen=True)
class CompleteEvent(AgentEvent):
    """The agent run has completed."""

    reason: str = ""
    final_message: str = ""
