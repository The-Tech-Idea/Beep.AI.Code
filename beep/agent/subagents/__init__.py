"""Sub-agent system for the autonomous agent runtime.

Enables the main agent to spawn specialized sub-agents
with isolated context and scoped tool access.
"""

from beep.agent.subagents.dispatcher import SubAgentDispatcher
from beep.agent.subagents.result_formatter import format_subagent_result

__all__ = ["SubAgentDispatcher", "format_subagent_result"]
