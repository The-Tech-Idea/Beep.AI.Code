"""Web search integration.

Fetches current information during conversations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SearchResult:
    """A web search result."""

    title: str
    url: str
    snippet: str


async def search_web(
    query: str,
    num_results: int = 5,
) -> list[SearchResult]:
    """Search the web for current information.

    Uses DuckDuckGo HTML interface (no API key needed).
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return [
            SearchResult(
                title="Search unavailable",
                url="",
                snippet="Install: pip install httpx beautifulsoup4",
            )
        ]

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                data={"q": query},
                headers=headers,
                follow_redirects=True,
            )

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for a in soup.select("a.result__a")[:num_results]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            snippet_el = a.find_next_sibling("a", class_="result__snippet")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            if title:
                results.append(SearchResult(
                    title=title,
                    url=href,
                    snippet=snippet[:200],
                ))

        return results

    except Exception:
        return [
            SearchResult(
                title="Search failed",
                url="",
                snippet="Could not complete web search",
            )
        ]


async def fetch_url(url: str, max_length: int = 5000) -> str:
    """Fetch and extract text content from a URL."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return "Install httpx and beautifulsoup4 to fetch URLs"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, follow_redirects=True)

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return text[:max_length]

    except Exception as exc:
        return f"Failed to fetch: {e}"
