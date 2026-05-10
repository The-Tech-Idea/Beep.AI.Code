"""Typed exceptions raised by BeepAPIClient."""

from __future__ import annotations


class BeepAPIError(Exception):
    """Raised when the server returns an HTTP error response.

    Carries the status code, the endpoint that was called, and the full
    server error message body so callers can surface actionable errors.
    """

    def __init__(
        self,
        status_code: int,
        endpoint: str,
        server_message: str,
    ) -> None:
        self.status_code = status_code
        self.endpoint = endpoint
        self.server_message = server_message
        super().__init__(
            f"HTTP {status_code} from {endpoint}: {server_message}"
        )
