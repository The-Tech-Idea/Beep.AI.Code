from __future__ import annotations

from unittest.mock import AsyncMock, patch

from beep.api.client import BeepAPIClient
from beep.api.endpoints import (
    V1_API_AGENTS_BUNDLES_IMPORT,
    V1_API_TOKENS_CHECK,
    V1_RAG_COLLECTIONS,
    V1_RAG_QUERY,
    V1_AGENT_CODING_EXECUTE,
    V1_AGENT_CODING_SESSIONS,
    V1_CHAT_COMPLETIONS,
    V1_EMBEDDINGS,
    V1_MESSAGES,
    V1_MODELS,
    V1_RESPONSES,
)
from beep.config import BeepConfig


def test_token_check_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(client, "_request", new=AsyncMock(return_value={"valid": True})) as req:
        import asyncio

        result = asyncio.run(client.check_token())
    assert result == {"valid": True}
    req.assert_awaited_once_with("GET", V1_API_TOKENS_CHECK)


def test_rag_query_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(client, "_request", new=AsyncMock(return_value={"results": []})) as req:
        import asyncio

        result = asyncio.run(client.rag_query("test query", collection="docs", top_k=3))
    assert result == {"results": []}
    req.assert_awaited_once_with(
        "POST",
        V1_RAG_QUERY,
        json={"query": "test query", "top_k": 3, "collection": "docs"},
    )


def test_rag_list_collections_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(client, "_request", new=AsyncMock(return_value={"collections": []})) as req:
        import asyncio

        result = asyncio.run(client.rag_list_collections())
    assert result == []
    req.assert_awaited_once_with("GET", V1_RAG_COLLECTIONS)


def test_import_agent_bundle_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(client, "_request", new=AsyncMock(return_value={"success": True})) as req:
        import asyncio

        result = asyncio.run(client.import_agent_bundle({"agent_id": "test"}, overwrite=False))
    assert result == {"success": True}
    req.assert_awaited_once_with(
        "POST",
        V1_API_AGENTS_BUNDLES_IMPORT,
        json={"bundle": {"agent_id": "test"}, "overwrite": False},
    )


def test_chat_completion_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(client, "_request", new=AsyncMock(return_value={"choices": []})) as req:
        import asyncio

        result = asyncio.run(client.chat_completion([{"role": "user", "content": "hello"}]))
    assert result == {"choices": []}


def test_chat_completion_event_stream_uses_v1_path(mock_config: BeepConfig) -> None:
    """Chat completion stream calls the correct /v1/chat/completions path."""
    import asyncio
    from unittest.mock import MagicMock, patch

    client = BeepAPIClient(mock_config)
    mock_http_client = MagicMock()
    mock_http_client.is_closed = False

    stream_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.aiter_lines.return_value.__aiter__.return_value = iter([])
    stream_ctx.__aenter__.return_value = mock_response
    stream_ctx.__aexit__.return_value = None
    mock_http_client.stream.return_value = stream_ctx

    client._client = mock_http_client

    async def _collect() -> None:
        try:
            async for _ in client.chat_completion_event_stream([{"role": "user", "content": "hi"}]):
                pass
        except Exception:
            pass

    asyncio.run(_collect())

    mock_http_client.stream.assert_called_once()
    call_args = mock_http_client.stream.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/v1/chat/completions"


def test_bootstrap_workspace_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(
        client, "_request", new=AsyncMock(return_value={"project_id": 1, "session_id": "s1"})
    ) as req:
        import asyncio

        result = asyncio.run(client.bootstrap_workspace("/tmp/test"))
    assert result == {"project_id": 1, "session_id": "s1"}
    req.assert_awaited_once_with(
        "POST",
        V1_AGENT_CODING_EXECUTE,
        json={
            "workspace_root": "/tmp/test",
            "create_project_if_missing": True,
            "create_session_if_missing": True,
            "interaction_mode": "inline",
        },
    )


def test_create_session_uses_v1_path(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(
        client, "_request", new=AsyncMock(return_value={"session_id": "s-new"})
    ) as req:
        import asyncio

        result = asyncio.run(client.create_session(project_id=42, title="test"))
    assert result == {"session_id": "s-new"}
    call_args = req.await_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == V1_AGENT_CODING_SESSIONS
    payload = call_args[1]["json"]
    assert payload["interaction_mode"] == "inline"
    assert payload["title"] == "test"
    assert "model_id" not in payload


def test_llm_endpoint_references_are_in_endpoints_module() -> None:
    """All LLM-facing path strings used in client_llm_support are catalogued."""
    import ast
    from pathlib import Path
    from beep.api import endpoints

    llm_support = Path(__file__).resolve().parent.parent / "beep" / "api" / "client_llm_support.py"
    tree = ast.parse(llm_support.read_text(encoding="utf-8"))
    paths_in_use: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("/v1/") and len(node.value) > 4:
                paths_in_use.add(node.value)

    endpoint_values: set[str] = set()
    for name in dir(endpoints):
        if name.startswith("_"):
            continue
        value = getattr(endpoints, name)
        if isinstance(value, str) and value.startswith("/v1/"):
            endpoint_values.add(value)

    uncovered = paths_in_use - endpoint_values
    known_prefix = {p + "/" for p in endpoint_values}
    acceptable = set()
    for p in uncovered:
        is_covered = any(p.startswith(prefix) for prefix in known_prefix)
        if is_covered:
            acceptable.add(p)
    truly_uncovered = uncovered - acceptable
    assert not truly_uncovered, f"Paths in client_llm_support not in endpoints: {truly_uncovered}"
