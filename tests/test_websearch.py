"""Tests for web search service, tool, and CLI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from beep.websearch.service import WebSearchService
from beep.websearch.search import SearchResult
from beep.agent.tools.web_search import WebSearchTool


class TestWebSearchService:
    @patch("beep.websearch.service.os.environ.get", return_value="1")
    def test_enabled(self, mock_get) -> None:
        service = WebSearchService()
        assert service.is_enabled() is True

    @patch("beep.websearch.service.os.environ.get", return_value="0")
    def test_disabled(self, mock_get) -> None:
        service = WebSearchService()
        assert service.is_enabled() is False

    @patch("beep.websearch.service.os.environ.get", return_value="0")
    def test_search_disabled(self, mock_get) -> None:
        import asyncio

        service = WebSearchService()
        results = asyncio.run(service.search("test"))
        assert len(results) == 1
        assert "disabled" in results[0].title.lower()

    @patch("beep.websearch.service.os.environ.get", return_value="1")
    def test_search_enabled_mocked(self, mock_get) -> None:
        import asyncio

        with patch("beep.websearch.service.search_web") as mock_search:
            mock_search.return_value = [
                SearchResult(title="Test", url="http://test.com", snippet="test")
            ]
            service = WebSearchService()
            results = asyncio.run(service.search("test"))
            assert len(results) == 1
            assert results[0].title == "Test"


class TestWebSearchTool:
    def test_tool_read_only_safe(self) -> None:
        tool = WebSearchTool()
        assert tool.read_only_safe is True

    def test_tool_parameters(self) -> None:
        tool = WebSearchTool()
        params = tool.parameters
        assert "query" in params
        assert "num_results" in params

    def test_no_query(self) -> None:
        import asyncio

        tool = WebSearchTool()
        result = asyncio.run(tool.execute(query=""))
        assert "No search query" in result.output

    @patch("beep.websearch.service.WebSearchService")
    def test_with_results(self, mock_svc_cls) -> None:
        import asyncio
        from unittest.mock import patch

        tool = WebSearchTool()
        instance = mock_svc_cls.return_value

        async def _mock_search(query, num_results=5):
            return [SearchResult(title="Result", url="http://example.com", snippet="snippet")]

        instance.search = _mock_search
        with patch("beep.app_service.get_app_service") as mock_app:
            mock_app.return_value.web_search = instance
            result = asyncio.run(tool.execute(query="test"))
        assert "Result" in result.output
        assert "http://example.com" in result.output


class TestSearchResult:
    def test_dataclass(self) -> None:
        r = SearchResult(title="T", url="http://u", snippet="s")
        assert r.title == "T"
        assert r.url == "http://u"
        assert r.snippet == "s"
