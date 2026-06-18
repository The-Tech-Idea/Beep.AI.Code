"""Verified MCP server presets for managed discovery definitions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from beep.config import MCPServerConfig
from beep.mcp.preset_tools import (
    CONTEXT7_TOOLS,
    FETCH_TOOLS,
    FILESYSTEM_TOOLS,
    FIRECRAWL_TOOLS,
    GITHUB_TOOLS,
    GLIF_TOOLS,
    PERPLEXITY_TOOLS,
    POSTGRES_TOOLS,
    SEMBLE_TOOLS,
    SENTRY_TOOLS,
    TAVILY_TOOLS,
)


@dataclass(frozen=True)
class McpPreset:
    """Verified launch metadata for a third-party MCP server."""

    key: str
    title: str
    description: str
    docs_url: str
    command: str
    args: tuple[str, ...]
    required_env: tuple[str, ...] = ()
    optional_env: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    tools: tuple[Any, ...] = ()
    windows_command: str | None = None
    windows_args: tuple[str, ...] | None = None

    def resolved_launch(self, *, is_windows: bool | None = None) -> tuple[str, list[str]]:
        """Return the verified launch command for the active platform."""
        use_windows = os.name == "nt" if is_windows is None else is_windows
        if use_windows and self.windows_command is not None:
            return self.windows_command, list(self.windows_args or ())
        return self.command, list(self.args)

    def build_server_definition(
        self,
        *,
        name: str | None = None,
        env_overrides: dict[str, str] | None = None,
        extra_args: list[str] | None = None,
        is_windows: bool | None = None,
    ) -> tuple[MCPServerConfig, dict[str, Any], list[str]]:
        """Build a managed server definition from this preset."""
        command, args = self.resolved_launch(is_windows=is_windows)
        env_map = dict(env_overrides or {})
        missing_required_env = [key for key in self.required_env if key not in env_map]

        config = MCPServerConfig(
            name=name or self.key,
            command=command,
            args=[*args, *(extra_args or [])],
            env=env_map,
            tools=list(self.tools),
        )

        metadata: dict[str, Any] = {
            "preset": self.key,
            "preset_title": self.title,
            "description": self.description,
            "docs_url": self.docs_url,
            "verification_scope": "launch-and-tool-metadata"
            if self.tools
            else "launch-metadata-only",
            "tool_contracts_included": bool(self.tools),
        }
        if self.tools:
            metadata["tool_names"] = [tool.name for tool in self.tools]
        if self.required_env:
            metadata["required_env"] = list(self.required_env)
        if self.optional_env:
            metadata["optional_env"] = list(self.optional_env)
        if self.notes:
            metadata["notes"] = list(self.notes)

        return config, metadata, missing_required_env


_PRESETS: tuple[McpPreset, ...] = (
    McpPreset(
        key="chrome-devtools",
        title="Chrome DevTools",
        description="Inspect and debug a Chrome browser session through Chrome DevTools MCP.",
        docs_url="https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session",
        command="npx",
        args=("-y", "chrome-devtools-mcp@latest"),
        notes=(
            "Use --arg --autoConnect to target a running Chrome session after enabling remote debugging.",
            "Windows uses cmd /c npx based on the official troubleshooting guidance.",
        ),
        aliases=("chrome",),
        windows_command="cmd",
        windows_args=("/c", "npx", "-y", "chrome-devtools-mcp@latest"),
    ),
    McpPreset(
        key="firecrawl",
        title="Firecrawl",
        description="Web search, scraping, crawl, and extraction tools from Firecrawl.",
        docs_url="https://github.com/firecrawl/firecrawl-mcp-server",
        command="npx",
        args=("-y", "firecrawl-mcp"),
        required_env=("FIRECRAWL_API_KEY",),
        optional_env=("FIRECRAWL_API_URL",),
        tools=FIRECRAWL_TOOLS,
        notes=(
            "Cloud API requires FIRECRAWL_API_KEY unless you point to a self-hosted FIRECRAWL_API_URL.",
        ),
    ),
    McpPreset(
        key="glif",
        title="Glif",
        description="Run and discover Glif workflows and optionally load agent tools.",
        docs_url="https://github.com/glifxyz/glif-mcp-server",
        command="npx",
        args=("-y", "@glifxyz/glif-mcp-server@latest"),
        required_env=("GLIF_API_TOKEN",),
        optional_env=("GLIF_IDS", "IGNORE_DISCOVERY_TOOLS", "AGENT_TOOLS"),
        tools=GLIF_TOOLS,
    ),
    McpPreset(
        key="perplexity",
        title="Perplexity",
        description="Perplexity search, ask, research, and reasoning MCP server.",
        docs_url="https://docs.perplexity.ai/guides/mcp-server",
        command="npx",
        args=("-y", "@perplexity-ai/mcp-server"),
        required_env=("PERPLEXITY_API_KEY",),
        aliases=("perplexity-mcp",),
        tools=PERPLEXITY_TOOLS,
    ),
    McpPreset(
        key="playwright",
        title="Playwright",
        description="Browser automation through Playwright MCP for page interaction and testing.",
        docs_url="https://playwright.dev/docs/getting-started-mcp",
        command="npx",
        args=("@playwright/mcp@latest",),
        notes=(
            "Pass --arg --headless to disable the headed browser.",
            "Pass --arg --browser=firefox to select a non-default browser.",
        ),
    ),
    McpPreset(
        key="semble",
        title="Semble",
        description=(
            "Fast CPU-only semantic code search over a local workspace or remote git repository. "
            "Exposes search and find_related tools for hybrid, semantic, and BM25 retrieval "
            "with no GPU or cloud dependency."
        ),
        docs_url="https://github.com/semble-ai/semble",
        command="uvx",
        args=("--from", "semble[mcp]", "semble"),
        tools=SEMBLE_TOOLS,
        notes=(
            "Requires uv to be installed (https://docs.astral.sh/uv/). "
            "semble[mcp] is installed automatically via uvx on first use.",
            "Index time is ~250 ms; query latency is ~1.5 ms on a typical laptop.",
            "Pass a workspace path as the first extra arg (--arg /path/to/repo) to pre-index a directory.",
        ),
        aliases=("semble-mcp",),
    ),
    McpPreset(
        key="github",
        title="GitHub MCP",
        description="GitHub issues, PRs, repository operations, and file management via the official GitHub MCP server.",
        docs_url="https://github.com/modelcontextprotocol/servers/tree/main/src/github",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-github"),
        required_env=("GITHUB_PERSONAL_ACCESS_TOKEN",),
        tools=GITHUB_TOOLS,
        notes=(
            "Requires a GitHub personal access token with appropriate scopes.",
            "Supports repository search, issue/PR management, file CRUD, and repository creation.",
        ),
    ),
    McpPreset(
        key="context7",
        title="Context7",
        description="Retrieve up-to-date library documentation and code examples with Context7's resolution and documentation tools.",
        docs_url="https://github.com/upstash/context7",
        command="npx",
        args=("-y", "@upstash/context7-mcp"),
        tools=CONTEXT7_TOOLS,
        notes=(
            "Uses Upstash-hosted Context7 service for library docs.",
            "Resolving a library ID first ensures accurate docs lookup.",
        ),
    ),
    McpPreset(
        key="tavily",
        title="Tavily Search MCP",
        description="Web search and content extraction using the Tavily API.",
        docs_url="https://tavily.com",
        command="npx",
        args=("-y", "tavily-mcp"),
        required_env=("TAVILY_API_KEY",),
        tools=TAVILY_TOOLS,
        notes=("TAVILY_API_KEY is required. Get one at https://tavily.com.",),
    ),
    McpPreset(
        key="postgres",
        title="PostgreSQL MCP",
        description="Read-only PostgreSQL database introspection and queries.",
        docs_url="https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-postgres"),
        required_env=("DATABASE_URL",),
        tools=POSTGRES_TOOLS,
        notes=(
            "Requires a DATABASE_URL connection string.",
            "All queries are read-only (SELECT only).",
        ),
    ),
    McpPreset(
        key="sentry",
        title="Sentry MCP",
        description="Sentry error context and issue monitoring via MCP.",
        docs_url="https://github.com/modelcontextprotocol/servers/tree/main/src/sentry",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-sentry"),
        required_env=("SENTRY_AUTH_TOKEN",),
        tools=SENTRY_TOOLS,
        notes=(
            "Requires a Sentry auth token with appropriate project access.",
            "Supports issue lookup, listing, and event inspection.",
        ),
    ),
    McpPreset(
        key="filesystem",
        title="Filesystem MCP",
        description="Sandboxed file system operations via MCP.",
        docs_url="https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-filesystem"),
        tools=FILESYSTEM_TOOLS,
        notes=(
            "Pass allowed paths via extra args (--arg /allowed/path).",
            "File operations are restricted to the specified paths.",
        ),
    ),
    McpPreset(
        key="fetch",
        title="Fetch MCP",
        description="URL fetching and web content retrieval, converting HTML to markdown.",
        docs_url="https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-fetch"),
        tools=FETCH_TOOLS,
        notes=(
            "Fetches URL content and converts to markdown or raw HTML.",
            "Supports batch URL fetching.",
        ),
    ),
)


_PRESET_INDEX = {
    lookup_key: preset for preset in _PRESETS for lookup_key in (preset.key, *preset.aliases)
}


def list_mcp_presets() -> list[McpPreset]:
    """Return all verified MCP presets sorted by key."""
    return list(_PRESETS)


def get_mcp_preset(name: str) -> McpPreset:
    """Resolve a preset by key or alias."""
    preset = _PRESET_INDEX.get(name.strip().lower())
    if preset is None:
        available = ", ".join(preset.key for preset in _PRESETS)
        raise ValueError(f"Unknown MCP preset '{name}'. Available presets: {available}.")
    return preset
