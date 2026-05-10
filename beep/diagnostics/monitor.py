"""Performance diagnostics and monitoring.

Provides:
- Token usage tracking
- Response time monitoring
- Cost estimation
- Session statistics
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from rich.table import Table



from beep.utils.console import get_console
@dataclass
class RequestMetrics:
    """Metrics for a single API request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    response_time: float = 0.0
    model: str = ""
    timestamp: float = 0.0


@dataclass
class SessionMetrics:
    """Aggregate session metrics."""

    requests: list[RequestMetrics] = field(default_factory=list)
    start_time: float = 0.0

    def __post_init__(self) -> None:
        if not self.start_time:
            self.start_time = time.time()

    @property
    def total_requests(self) -> int:
        return len(self.requests)

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.requests)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(r.prompt_tokens for r in self.requests)

    @property
    def total_completion_tokens(self) -> int:
        return sum(r.completion_tokens for r in self.requests)

    @property
    def avg_response_time(self) -> float:
        if not self.requests:
            return 0.0
        return sum(r.response_time for r in self.requests) / len(self.requests)

    @property
    def duration(self) -> float:
        return time.time() - self.start_time

    def add_request(self, metrics: RequestMetrics) -> None:
        """Record a request."""
        self.requests.append(metrics)

    def estimate_cost(self, price_per_million: float = 3.0) -> float:
        """Estimate cost based on token usage."""
        return (self.total_tokens / 1_000_000) * price_per_million


def display_diagnostics(metrics: SessionMetrics) -> None:
    """Display session diagnostics."""
    get_console().print("[bold]Session Diagnostics[/bold]\n")

    table = Table(title="Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    mins, secs = divmod(metrics.duration, 60)
    table.add_row("Duration", f"{int(mins)}m {int(secs)}s")
    table.add_row("Requests", str(metrics.total_requests))
    table.add_row("Total Tokens", f"{metrics.total_tokens:,}")
    table.add_row("Prompt Tokens", f"{metrics.total_prompt_tokens:,}")
    table.add_row("Completion Tokens", f"{metrics.total_completion_tokens:,}")
    table.add_row("Avg Response Time", f"{metrics.avg_response_time:.2f}s")

    get_console().print(table)

    if metrics.requests:
        table = Table(title="Recent Requests")
        table.add_column("#", justify="right")
        table.add_column("Model", style="cyan")
        table.add_column("Prompt", justify="right")
        table.add_column("Completion", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Time", justify="right")

        for i, req in enumerate(metrics.requests[-10:], 1):
            table.add_row(
                str(i),
                req.model,
                f"{req.prompt_tokens:,}",
                f"{req.completion_tokens:,}",
                f"{req.total_tokens:,}",
                f"{req.response_time:.2f}s",
            )

        get_console().print(table)
