"""Verified static tool contracts for MCP presets."""

from __future__ import annotations

from typing import Any

from beep.config import MCPToolConfig


def _tool(name: str, description: str, parameters: dict[str, Any]) -> MCPToolConfig:
    return MCPToolConfig(name=name, description=description, parameters=parameters)


def _string(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "string", "description": description, **extra}


def _number(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "number", "description": description, **extra}


def _integer(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "integer", "description": description, **extra}


def _boolean(description: str, **extra: Any) -> dict[str, Any]:
    return {"type": "boolean", "description": description, **extra}


def _array(description: str, items: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"type": "array", "description": description, "items": items, **extra}


def _object(description: str, properties: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "object", "description": description}
    if properties is not None:
        payload["properties"] = properties
    payload.update(extra)
    return payload


_message_item = _object(
    "Conversation message.",
    properties={
        "role": _string(
            "Role of the message sender.",
            enum=["system", "user", "assistant"],
        ),
        "content": _string("Message content."),
    },
    required=["role", "content"],
)

_search_recency_filter = _string(
    "Filter results by recency.",
    enum=["hour", "day", "week", "month", "year"],
)

_search_domain_filter = _array(
    "Restrict results to specific domains; prefix with '-' to exclude a domain.",
    _string("Domain filter entry."),
)

_search_context_size = _string(
    "Controls how much web context is retrieved.",
    enum=["low", "medium", "high"],
)

_reasoning_effort = _string(
    "Controls reasoning depth for deep research.",
    enum=["minimal", "low", "medium", "high"],
)

_formats_field = _array(
    "Requested output formats. Supports simple strings such as markdown or branding, or JSON format descriptors.",
    {
        "anyOf": [
            _string("Named output format."),
            _object(
                "Structured format descriptor.",
                properties={
                    "type": _string("Structured format kind, such as json."),
                    "prompt": _string("Extraction prompt for JSON output."),
                    "schema": _object("JSON schema describing the desired extraction result."),
                },
                required=["type"],
            ),
        ]
    },
)


FIRECRAWL_TOOLS: tuple[MCPToolConfig, ...] = (
    _tool(
        "firecrawl_scrape",
        "Scrape content from a single URL with structured or markdown output.",
        {
            "url": _string("URL to scrape."),
            "formats": _formats_field,
            "onlyMainContent": _boolean("Whether to keep only the main page content."),
        },
    ),
    _tool(
        "firecrawl_batch_scrape",
        "Scrape multiple known URLs in one batch job.",
        {
            "urls": _array("URLs to scrape.", _string("Target URL.")),
            "options": _object(
                "Batch scrape options.",
                properties={
                    "formats": _array("Requested output formats.", _string("Format name.")),
                    "onlyMainContent": _boolean("Whether to keep only main content."),
                },
            ),
        },
    ),
    _tool(
        "firecrawl_check_batch_status",
        "Check the status of a Firecrawl batch scrape job.",
        {
            "id": _string("Batch operation ID."),
        },
    ),
    _tool(
        "firecrawl_map",
        "Discover indexed URLs on a site.",
        {
            "url": _string("Site URL to map."),
        },
    ),
    _tool(
        "firecrawl_search",
        "Search the web and optionally scrape the returned results.",
        {
            "query": _string("Search query."),
            "limit": _integer("Maximum number of results to return."),
            "lang": _string("Language code for the search."),
            "country": _string("Country code for the search."),
            "scrapeOptions": _object(
                "Optional scrape settings to apply to returned results.",
                properties={
                    "formats": _array("Requested output formats.", _string("Format name.")),
                    "onlyMainContent": _boolean("Whether to keep only main content."),
                },
            ),
        },
    ),
    _tool(
        "firecrawl_crawl",
        "Start an asynchronous crawl over a site or section.",
        {
            "url": _string("Root URL or URL pattern to crawl."),
            "maxDepth": _integer("Maximum crawl depth."),
            "limit": _integer("Maximum number of pages to crawl."),
            "allowExternalLinks": _boolean("Whether external links may be followed."),
            "deduplicateSimilarURLs": _boolean("Whether similar URLs should be deduplicated."),
        },
    ),
    _tool(
        "firecrawl_check_crawl_status",
        "Check the status of an asynchronous crawl job.",
        {
            "id": _string("Crawl job ID."),
        },
    ),
    _tool(
        "firecrawl_extract",
        "Extract structured information from one or more pages.",
        {
            "urls": _array("URLs to extract from.", _string("Target URL.")),
            "prompt": _string("Extraction prompt."),
            "systemPrompt": _string("Optional system prompt guiding extraction."),
            "schema": _object("JSON schema describing the desired structured result."),
            "allowExternalLinks": _boolean("Whether extraction may follow external links."),
            "enableWebSearch": _boolean("Whether web search may be used as extra context."),
            "includeSubdomains": _boolean("Whether subdomains may be included during extraction."),
        },
    ),
    _tool(
        "firecrawl_agent",
        "Run Firecrawl's asynchronous autonomous research agent.",
        {
            "prompt": _string("Research prompt describing the data to gather."),
            "urls": _array("Optional URLs to focus the agent on.", _string("Target URL.")),
            "schema": _object("Optional JSON schema for structured output."),
        },
    ),
    _tool(
        "firecrawl_agent_status",
        "Check the status of a Firecrawl agent job.",
        {
            "id": _string("Agent job ID."),
        },
    ),
)


GLIF_TOOLS: tuple[MCPToolConfig, ...] = (
    _tool(
        "run_workflow",
        "Run a Glif workflow with the specified workflow ID and ordered inputs.",
        {
            "id": _string("Workflow ID to run."),
            "inputs": _array(
                "Ordered workflow inputs. May include text, media URLs, or base64-encoded media.",
                _string("Workflow input value."),
            ),
        },
    ),
    _tool(
        "workflow_info",
        "Get detailed information about a Glif workflow.",
        {
            "id": _string("Workflow ID to inspect."),
        },
    ),
    _tool(
        "list_featured_workflows",
        "Get a curated list of featured Glif workflows.",
        {},
    ),
    _tool(
        "search_workflows",
        "Search Glif workflows by name, description, or keywords.",
        {
            "query": _string("Search query string."),
        },
    ),
    _tool(
        "my_workflows",
        "List your published Glif workflows.",
        {},
    ),
    _tool(
        "my_user_info",
        "Get detailed information about your Glif account.",
        {},
    ),
    _tool(
        "list_agents",
        "List Glif agents with optional filtering and sorting.",
        {
            "sort": _string(
                "Optional sort order.",
                enum=["new", "popular", "featured"],
            ),
            "username": _string("Optional creator username filter."),
            "searchQuery": _string("Optional text search query."),
        },
    ),
    _tool(
        "load_agent",
        "Load a specific Glif agent and return its details.",
        {
            "id": _string("Agent ID to load."),
        },
    ),
)


PERPLEXITY_TOOLS: tuple[MCPToolConfig, ...] = (
    _tool(
        "perplexity_search",
        "Search the web and return ranked results with titles, URLs, snippets, and dates.",
        {
            "query": _string("Search query string."),
            "max_results": _integer("Maximum number of results to return.", minimum=1, maximum=20),
            "max_tokens_per_page": _integer(
                "Maximum tokens to extract per webpage.",
                minimum=256,
                maximum=2048,
            ),
            "country": _string("ISO 3166-1 alpha-2 country code for regional results."),
        },
    ),
    _tool(
        "perplexity_ask",
        "Answer a question using the Sonar Pro model with web grounding and citations.",
        {
            "messages": _array("Conversation messages.", _message_item),
            "search_recency_filter": _search_recency_filter,
            "search_domain_filter": _search_domain_filter,
            "search_context_size": _search_context_size,
        },
    ),
    _tool(
        "perplexity_research",
        "Run deep multi-source research with the Sonar Deep Research model.",
        {
            "messages": _array("Conversation messages.", _message_item),
            "strip_thinking": _boolean("Remove <think> blocks from the response."),
            "reasoning_effort": _reasoning_effort,
        },
    ),
    _tool(
        "perplexity_reason",
        "Use the Sonar Reasoning Pro model for analytical and step-by-step reasoning.",
        {
            "messages": _array("Conversation messages.", _message_item),
            "strip_thinking": _boolean("Remove <think> blocks from the response."),
            "search_recency_filter": _search_recency_filter,
            "search_domain_filter": _search_domain_filter,
            "search_context_size": _search_context_size,
        },
    ),
)


SEMBLE_TOOLS: tuple[MCPToolConfig, ...] = (
    _tool(
        "search",
        "Search a local workspace or remote git repository with Semble hybrid, semantic, or BM25 retrieval. "
        "Returns ranked code chunks with file paths, line ranges, scores, and content snippets.",
        {
            "query": _string("Natural-language or code query to search for."),
            "path": _string(
                "Local directory to index. Omit to use the server's default workspace root.",
            ),
            "git_url": _string(
                "Remote git repository URL (e.g. https://github.com/org/repo) to index instead of a local path.",
            ),
            "top_k": _integer(
                "Maximum number of results to return. Defaults to 5. Maximum is 20.",
                minimum=1,
                maximum=20,
            ),
            "mode": _string(
                "Search mode: hybrid (default), semantic, or bm25.",
                enum=["hybrid", "semantic", "bm25"],
            ),
            "filter_languages": _array(
                "Restrict results to these programming languages, e.g. ['python', 'typescript'].",
                _string("Language name."),
            ),
            "filter_paths": _array(
                "Restrict retrieval to these workspace-relative file paths.",
                _string("Workspace-relative file path."),
            ),
        },
    ),
    _tool(
        "find_related",
        "Return code chunks semantically similar to a specific file and line using the Semble index. "
        "Use after search to explore related implementations across the codebase.",
        {
            "file_path": _string(
                "Workspace-relative or absolute path to the file containing the reference chunk.",
            ),
            "line": _integer(
                "1-based line number inside the file that anchors the related-code lookup.",
                minimum=1,
            ),
            "path": _string(
                "Local directory root to index. Omit to use the server's default workspace root.",
            ),
            "git_url": _string(
                "Remote git repository URL to index instead of a local path.",
            ),
            "top_k": _integer(
                "Maximum number of related chunks to return. Defaults to 5. Maximum is 20.",
                minimum=1,
                maximum=20,
            ),
        },
    ),
)