"""Curated integrations catalog — code-first registry of skills, MCP servers, and dev tools."""

from __future__ import annotations

from beep.integrations.models import CatalogEntry, EntryKind, TrustTier

CURATED_ENTRIES: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        id="open-design",
        kind=EntryKind.skill,
        name="Open Design",
        summary="Design systems, UI/prototype/slide/image generation skill.",
        source_url="https://github.com/nexu-io/open-design",
        version="main",
        trust=TrustTier.external,
        requires_network=True,
        tags=["design", "ui", "prototype", "image", "slides"],
    ),
    CatalogEntry(
        id="graphify",
        kind=EntryKind.skill,
        name="Graphify",
        summary="Turn a repo (code, SQL, docs) into a queryable knowledge graph.",
        source_url="https://github.com/safishamsi/graphify",
        version="main",
        trust=TrustTier.external,
        requires_network=True,
        tags=["graph", "knowledge-graph", "code-analysis", "sql", "docs"],
    ),
    CatalogEntry(
        id="code-review",
        kind=EntryKind.skill,
        name="Code Review",
        summary="Standards-aware code review preset.",
        source_url="",
        version="1.0.0",
        trust=TrustTier.first_party,
        tags=["review", "standards", "quality"],
    ),
    CatalogEntry(
        id="test-author",
        kind=EntryKind.skill,
        name="Test Author",
        summary="Test generation preset for unit, integration, and edge-case tests.",
        source_url="",
        version="1.0.0",
        trust=TrustTier.first_party,
        tags=["testing", "generation", "quality"],
    ),
    CatalogEntry(
        id="github-mcp",
        kind=EntryKind.mcp,
        name="GitHub MCP",
        summary="GitHub issues, PRs, and repository operations via MCP.",
        source_url="https://github.com/modelcontextprotocol/servers",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["github", "issues", "prs", "git"],
    ),
    CatalogEntry(
        id="playwright-mcp",
        kind=EntryKind.mcp,
        name="Playwright MCP",
        summary="Browser automation through Playwright for page interaction and e2e testing.",
        source_url="https://playwright.dev/docs/getting-started-mcp",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["browser", "automation", "e2e", "testing"],
    ),
    CatalogEntry(
        id="context7-mcp",
        kind=EntryKind.mcp,
        name="Context7",
        summary="Up-to-date library documentation via MCP.",
        source_url="https://github.com/upstash/context7",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["docs", "libraries", "context"],
    ),
    CatalogEntry(
        id="tavily-mcp",
        kind=EntryKind.mcp,
        name="Tavily Search",
        summary="Web search via Tavily API.",
        source_url="https://tavily.com",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["search", "web", "tavily"],
    ),
    CatalogEntry(
        id="postgres-mcp",
        kind=EntryKind.mcp,
        name="PostgreSQL MCP",
        summary="Database introspection and queries for PostgreSQL.",
        source_url="https://github.com/modelcontextprotocol/servers",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["database", "postgres", "sql"],
    ),
    CatalogEntry(
        id="sentry-mcp",
        kind=EntryKind.mcp,
        name="Sentry MCP",
        summary="Error context and monitoring via Sentry.",
        source_url="https://github.com/modelcontextprotocol/servers",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["monitoring", "errors", "sentry"],
    ),
    CatalogEntry(
        id="filesystem-mcp",
        kind=EntryKind.mcp,
        name="Filesystem MCP",
        summary="Sandboxed file system operations via MCP.",
        source_url="https://github.com/modelcontextprotocol/servers",
        version="latest",
        trust=TrustTier.verified,
        tags=["filesystem", "sandbox"],
    ),
    CatalogEntry(
        id="fetch-mcp",
        kind=EntryKind.mcp,
        name="Fetch MCP",
        summary="URL fetching and web content retrieval via MCP.",
        source_url="https://github.com/modelcontextprotocol/servers",
        version="latest",
        trust=TrustTier.verified,
        requires_network=True,
        tags=["fetch", "web", "http"],
    ),
    CatalogEntry(
        id="ripgrep",
        kind=EntryKind.tool,
        name="ripgrep (rg)",
        summary="Ultra-fast recursive text search.",
        source_url="https://github.com/BurntSushi/ripgrep",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: cargo install ripgrep or your system package manager",
        tags=["search", "grep", "cli"],
    ),
    CatalogEntry(
        id="fd",
        kind=EntryKind.tool,
        name="fd",
        summary="Fast, user-friendly alternative to find.",
        source_url="https://github.com/sharkdp/fd",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: cargo install fd-find or your system package manager",
        tags=["find", "cli"],
    ),
    CatalogEntry(
        id="gh",
        kind=EntryKind.tool,
        name="GitHub CLI",
        summary="GitHub command-line tool for issues, PRs, and repo management.",
        source_url="https://github.com/cli/cli",
        version="",
        trust=TrustTier.verified,
        requires_network=True,
        install_hint="Install via: https://cli.github.com",
        tags=["github", "cli", "git"],
    ),
    CatalogEntry(
        id="semgrep",
        kind=EntryKind.tool,
        name="Semgrep",
        summary="Fast static analysis for finding bugs and enforcing code standards.",
        source_url="https://github.com/semgrep/semgrep",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: pip install semgrep",
        tags=["lint", "security", "static-analysis"],
    ),
    CatalogEntry(
        id="ruff",
        kind=EntryKind.tool,
        name="Ruff",
        summary="Extremely fast Python linter and code formatter.",
        source_url="https://github.com/astral-sh/ruff",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: pip install ruff",
        tags=["python", "lint", "format"],
    ),
    CatalogEntry(
        id="mypy",
        kind=EntryKind.tool,
        name="Mypy",
        summary="Static type checker for Python.",
        source_url="https://github.com/python/mypy",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: pip install mypy",
        tags=["python", "types", "lint"],
    ),
    CatalogEntry(
        id="eslint",
        kind=EntryKind.tool,
        name="ESLint",
        summary="Pluggable linting utility for JavaScript and TypeScript.",
        source_url="https://github.com/eslint/eslint",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: npm install -g eslint",
        tags=["javascript", "lint"],
    ),
    CatalogEntry(
        id="prettier",
        kind=EntryKind.tool,
        name="Prettier",
        summary="Opinionated code formatter for JavaScript, TypeScript, CSS, and more.",
        source_url="https://github.com/prettier/prettier",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: npm install -g prettier",
        tags=["format", "javascript", "css"],
    ),
    CatalogEntry(
        id="jq",
        kind=EntryKind.tool,
        name="jq",
        summary="Lightweight and flexible command-line JSON processor.",
        source_url="https://github.com/jqlang/jq",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via your system package manager",
        tags=["json", "cli"],
    ),
    CatalogEntry(
        id="docker",
        kind=EntryKind.tool,
        name="Docker",
        summary="Container runtime and orchestration.",
        source_url="https://docs.docker.com/get-docker",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: https://docs.docker.com/get-docker",
        tags=["containers", "devops"],
    ),
    CatalogEntry(
        id="node",
        kind=EntryKind.tool,
        name="Node.js",
        summary="JavaScript runtime built on Chrome's V8 engine.",
        source_url="https://nodejs.org",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via: https://nodejs.org or nvm",
        tags=["javascript", "runtime"],
    ),
    CatalogEntry(
        id="git",
        kind=EntryKind.tool,
        name="Git",
        summary="Distributed version control system.",
        source_url="https://git-scm.com",
        version="",
        trust=TrustTier.verified,
        install_hint="Install via your system package manager",
        tags=["vcs", "cli"],
    ),
)


_ENTRY_INDEX: dict[str, CatalogEntry] = {entry.id: entry for entry in CURATED_ENTRIES}


def _validate_catalog() -> None:
    seen: set[str] = set()
    for entry in CURATED_ENTRIES:
        if entry.id in seen:
            raise ValueError(f"Duplicate catalog entry id: {entry.id}")
        seen.add(entry.id)
        if entry.trust == TrustTier.external and not entry.requires_network:
            raise ValueError(f"External entry '{entry.id}' must set requires_network=True")


_validate_catalog()


def find(entry_id: str) -> CatalogEntry | None:
    return _ENTRY_INDEX.get(entry_id)


def search(query: str, kind: EntryKind | None = None) -> list[CatalogEntry]:
    q = query.lower()
    results: list[CatalogEntry] = []
    for entry in CURATED_ENTRIES:
        if kind is not None and entry.kind != kind:
            continue
        if q in entry.id.lower() or q in entry.name.lower() or q in entry.summary.lower():
            results.append(entry)
            continue
        if any(q in tag.lower() for tag in entry.tags):
            results.append(entry)
    return results
