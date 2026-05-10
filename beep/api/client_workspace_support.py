"""Workspace, RAG, and token endpoint helpers for the API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from beep.api.client import BeepAPIClient


class BeepAPIClientWorkspaceMixin:
    async def compact_conversation(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await compact_conversation(self, session_id=session_id, messages=messages)

    async def bootstrap_workspace(
        self,
        workspace_root: str,
        *,
        create_project_if_missing: bool = True,
        create_session_if_missing: bool = True,
        interaction_mode: str = "inline",
        model_id: str | None = None,
    ) -> dict[str, Any]:
        return await bootstrap_workspace(
            self,
            workspace_root=workspace_root,
            create_project_if_missing=create_project_if_missing,
            create_session_if_missing=create_session_if_missing,
            interaction_mode=interaction_mode,
            model_id=model_id,
        )

    async def bootstrap_project(
        self,
        project_id: int,
        *,
        session_id: str | None = None,
        interaction_mode: str = "inline",
        model_id: str | None = None,
        include_coding_tools: bool = True,
    ) -> dict[str, Any]:
        return await bootstrap_project(
            self,
            project_id=project_id,
            session_id=session_id,
            interaction_mode=interaction_mode,
            model_id=model_id,
            include_coding_tools=include_coding_tools,
        )

    async def create_session(
        self,
        project_id: int,
        title: str | None = None,
        model_id: str | None = None,
        interaction_mode: str = "inline",
    ) -> dict[str, Any]:
        return await create_session(
            self,
            project_id=project_id,
            title=title,
            model_id=model_id,
            interaction_mode=interaction_mode,
        )

    async def list_sessions(self, project_id: int) -> list[dict[str, Any]]:
        return await list_sessions(self, project_id=project_id)

    async def rag_query(
        self,
        query: str,
        *,
        collection: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        return await rag_query(self, query=query, collection=collection, top_k=top_k)

    async def rag_list_collections(self) -> list[dict[str, Any]]:
        return await rag_list_collections(self)

    async def check_token(self) -> dict[str, Any]:
        return await check_token(self)


async def compact_conversation(
    client: BeepAPIClient,
    *,
    session_id: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session_id": session_id,
        "messages": messages,
    }
    return await client._request(
        "POST",
        "/v1/api/agent-framework/agents/beep.agent.coding/execute",
        json=payload,
    )


async def bootstrap_workspace(
    client: BeepAPIClient,
    *,
    workspace_root: str,
    create_project_if_missing: bool = True,
    create_session_if_missing: bool = True,
    interaction_mode: str = "inline",
    model_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "workspace_root": workspace_root,
        "create_project_if_missing": create_project_if_missing,
        "create_session_if_missing": create_session_if_missing,
        "interaction_mode": interaction_mode,
    }
    if model_id:
        payload["model_id"] = model_id
    return await client._request(
        "POST",
        "/v1/api/agent-framework/agents/beep.agent.coding/execute",
        json=payload,
    )


async def bootstrap_project(
    client: BeepAPIClient,
    *,
    project_id: int,
    session_id: str | None = None,
    interaction_mode: str = "inline",
    model_id: str | None = None,
    include_coding_tools: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "interaction_mode": interaction_mode,
        "include_coding_tools": include_coding_tools,
    }
    if session_id:
        payload["session_id"] = session_id
    if model_id:
        payload["model_id"] = model_id
    return await client._request(
        "POST",
        "/v1/api/agent-framework/agents/beep.agent.coding/execute",
        json=payload,
    )


async def create_session(
    client: BeepAPIClient,
    *,
    project_id: int,
    title: str | None = None,
    model_id: str | None = None,
    interaction_mode: str = "inline",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"interaction_mode": interaction_mode}
    if title:
        payload["title"] = title
    if model_id:
        payload["model_id"] = model_id
    return await client._request(
        "POST",
        "/v1/api/agent-framework/agents/beep.agent.coding/sessions",
        json=payload,
    )


async def list_sessions(client: BeepAPIClient, *, project_id: int) -> list[dict[str, Any]]:
    result = await client._request(
        "GET",
        "/v1/api/agent-framework/agents/beep.agent.coding/sessions",
    )
    return result.get("sessions", [])


async def rag_query(
    client: BeepAPIClient,
    *,
    query: str,
    collection: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query, "top_k": top_k}
    if collection:
        payload["collection"] = collection
    return await client._request("POST", "/v1/api/rag/query", json=payload)


async def rag_list_collections(client: BeepAPIClient) -> list[dict[str, Any]]:
    result = await client._request("GET", "/v1/api/rag/collections")
    return result.get("collections", [])


async def check_token(client: BeepAPIClient) -> dict[str, Any]:
    return await client._request("GET", "/v1/api/tokens/check")


async def fetch_server_skills(client: BeepAPIClient) -> list[dict[str, Any]]:
    """Fetch global skills from the server."""
    result = await client._request("GET", "/v1/api/agent-framework/agents/beep.agent.coding/skills")
    return result.get("skills", [])
