"""Agent roster — manages available agents based on the user's profile.

Provides agent switching, profile-to-agent mapping, and the
system prompt augmentation that makes each agent behave differently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from beep.profiles import UserProfile
from beep.profiles.layer_catalog import LayerInfo, get_layer_catalog


def _get_active_profile() -> UserProfile | None:
    """Get the currently active profile, or None."""
    from beep.profiles import has_saved_profile, load_active_profile
    if not has_saved_profile():
        return None
    return load_active_profile()


@dataclass
class AgentContext:
    """The currently active agent context in a chat session."""

    agent_id: str
    display_name: str
    description: str = ""
    system_prompt_augmentation: str = ""
    layer_id: str | None = None        # Linked specialty layer
    tools: list[str] = field(default_factory=list)


class AgentRoster:
    """Manages available agents for the current profile.

    Usage:
        roster = AgentRoster()
        await roster.load_from_server(client)
        ctx = roster.activate("react_developer")
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentContext] = {}
        self._active: AgentContext | None = None
        self._profile_id: str | None = None

    @property
    def active(self) -> AgentContext | None:
        return self._active

    async def load_from_server(self, client: Any, api_token: str | None = None) -> None:
        """Load available agents from the server's layer catalog."""
        catalog = get_layer_catalog()
        if not catalog.is_loaded:
            await catalog.refresh(client, api_token)

        profile = _get_profile()
        if profile is None:
            return

        self._profile_id = profile.profile_id
        layers = catalog.for_profile(profile.profile_id)

        for layer in layers:
            self._agents[layer.id] = AgentContext(
                agent_id=layer.id,
                display_name=layer.name,
                description=layer.description,
                layer_id=layer.id,
                tools=layer.tools,
            )

        # Add profile-specific agents that may not be layers
        self._add_profile_agents(profile)

        # Set default active agent
        if self._agents and self._active is None:
            first = next(iter(self._agents.values()))
            self._active = first

    def _add_profile_agents(self, profile: UserProfile) -> None:
        """Add profile-specific built-in agents."""
        builtins: dict[str, dict[str, Any]] = {
            "team_lead_dev": {
                "code_reviewer": {"name": "Code Reviewer", "desc": "Reviews code for bugs, security, and best practices"},
                "bug_fixer": {"name": "Bug Finder", "desc": "Traces and explains issues in your code"},
                "test_writer": {"name": "Test Writer", "desc": "Generates unit, integration, and E2E tests"},
            },
            "business_analyst": {
                "requirements_analyst": {"name": "Smart Analysis", "desc": "Ask questions about documents and get answers"},
                "process_mapper": {"name": "Process Mapping", "desc": "Visualize workflows and processes"},
            },
        }

        for agent_id, info in builtins.get(profile.profile_id, {}).items():
            if agent_id not in self._agents:
                self._agents[agent_id] = AgentContext(
                    agent_id=agent_id,
                    display_name=info["name"],
                    description=info["desc"],
                )

    def activate(self, agent_id: str) -> AgentContext | None:
        """Switch to a different agent."""
        ctx = self._agents.get(agent_id)
        if ctx is None:
            return None
        self._active = ctx
        return ctx

    def list_agents(self) -> list[AgentContext]:
        """List all available agents for the current profile."""
        return list(self._agents.values())

    def find_agent(self, query: str) -> list[AgentContext]:
        """Search agents by name or ID."""
        q = query.lower()
        return [
            a for a in self._agents.values()
            if q in a.agent_id.lower() or q in a.display_name.lower()
        ]

    def get_system_prompt_for_active(self) -> str:
        """Get the system prompt augmentation for the active agent."""
        if self._active is None:
            return ""

        prompt_augmentations: dict[str, str] = {
            "code_reviewer": (
                "Act as an expert code reviewer. Focus on correctness, security, "
                "performance, and best practices. Flag issues with severity levels."
            ),
            "bug_fixer": (
                "Act as a bug-finding expert. Trace issues to root causes, explain "
                "the chain of events, and suggest minimal fixes."
            ),
            "test_writer": (
                "Act as a test-writing expert. Generate comprehensive tests covering "
                "happy paths, edge cases, and error conditions."
            ),
            "react_developer": (
                "Act as a React specialist. Follow React best practices, hooks patterns, "
                "and modern component architecture. Prefer functional components with TypeScript."
            ),
            "contract_reviewer": (
                "Act as a legal document reviewer. Flag risky clauses, suggest alternative "
                "language, and highlight missing protections."
            ),
        }

        base = prompt_augmentations.get(self._active.agent_id, "")
        if base:
            return base

        # Fallback: describe the agent's role
        return f"Act as a {self._active.display_name}. {self._active.description}"


# Singleton
_roster: AgentRoster | None = None


def get_agent_roster() -> AgentRoster:
    """Get the singleton agent roster."""
    global _roster
    if _roster is None:
        _roster = AgentRoster()
    return _roster
