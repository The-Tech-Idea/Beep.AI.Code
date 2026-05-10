"""Session manager combining local history with server sessions."""

from __future__ import annotations

from typing import Any

from beep.api.client import BeepAPIClient
from beep.config import BeepConfig
from beep.sessions.history import (
    create_session_id,
    delete_session,
    list_sessions,
    load_session,
    save_message,
)


class SessionManager:
    """Manages chat sessions with local history and optional server sync."""

    def __init__(self, config: BeepConfig, client: BeepAPIClient | None = None) -> None:
        self._config = config
        self._client = client
        self._current_session_id: str | None = None
        self._messages: list[dict[str, Any]] = []

    @property
    def current_session_id(self) -> str | None:
        return self._current_session_id

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self._messages

    def new_session(self) -> str:
        """Create a new session."""
        self._current_session_id = create_session_id()
        self._messages = []
        return self._current_session_id

    def load_session(self, session_id: str) -> list[dict[str, Any]]:
        """Load a session from local history."""
        self._current_session_id = session_id
        self._messages = load_session(session_id)
        return self._messages

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the current session."""
        if not self._current_session_id:
            self.new_session()

        message = {"role": role, "content": content}
        self._messages.append(message)
        save_message(self._current_session_id, message)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all local sessions."""
        return list_sessions()

    def delete_session(self, session_id: str) -> bool:
        """Delete a local session."""
        if self._current_session_id == session_id:
            self._current_session_id = None
            self._messages = []
        return delete_session(session_id)

    async def create_server_session(
        self,
        project_id: int | None = None,
        title: str | None = None,
    ) -> str | None:
        """Create a session on the server."""
        if not self._client:
            return None

        pid = project_id or self._config.project_id
        if not pid:
            return None

        try:
            result = await self._client.create_session(pid, title=title)
            server_id = result.get("session_id")
            if server_id and self._current_session_id:
                save_message(self._current_session_id, {
                    "role": "system",
                    "content": f"Server session: {server_id}",
                })
            return server_id
        except Exception:
            return None

    async def list_server_sessions(self) -> list[dict[str, Any]]:
        """List sessions from the server."""
        if not self._client:
            return []

        pid = self._config.project_id
        if not pid:
            return []

        try:
            return await self._client.list_sessions(pid)
        except Exception:
            return []
