"""Parallel agent coordinator — run N agents concurrently in isolated worktrees."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CoordinatedResult:
    run_id: str
    goal: str
    success: bool
    summary: str = ""
    error: str = ""


@dataclass
class FanOutResult:
    results: list[CoordinatedResult] = field(default_factory=list)
    combined_summary: str = ""

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)


class ParallelCoordinator:
    """Launch multiple agents concurrently, each in its own git worktree."""

    def __init__(
        self,
        workspace_root: Path,
        *,
        max_workers: int = 4,
    ) -> None:
        self._workspace_root = workspace_root
        self._max_workers = max_workers

    async def fan_out(
        self,
        goal: str,
        worker_count: int = 2,
        *,
        run_agent_fn: Any = None,
    ) -> FanOutResult:
        from beep.agent.parallel.worktrees import WorktreeManager

        if run_agent_fn is None:
            result = FanOutResult()
            result.combined_summary = (
                "No agent runner provided. Install `beep agent` to run agents."
            )
            return result

        manager = WorktreeManager(self._workspace_root)
        semaphore = asyncio.Semaphore(min(worker_count, self._max_workers))
        results: list[CoordinatedResult] = []

        async def _worker(index: int) -> None:
            async with semaphore:
                run_id = f"agent-{index}"
                worktree_path = Path(".")
                worktree_created = False
                try:
                    run_id, worktree_path = manager.create(run_id)
                    worktree_created = True
                    result = await run_agent_fn(
                        goal=goal,
                        workspace_root=worktree_path,
                        run_id=run_id,
                    )
                    results.append(
                        CoordinatedResult(
                            run_id=run_id,
                            goal=goal,
                            success=True,
                            summary=str(result),
                        )
                    )
                except Exception as exc:
                    results.append(
                        CoordinatedResult(
                            run_id=run_id,
                            goal=goal,
                            success=False,
                            error=str(exc),
                        )
                    )
                finally:
                    if worktree_created:
                        try:
                            manager.cleanup(run_id)
                        except Exception:
                            pass

        tasks = [_worker(i) for i in range(worker_count)]
        await asyncio.gather(*tasks)

        successes = sum(1 for r in results if r.success)
        summaries = [r.summary for r in results if r.summary]
        combined = f"{successes}/{len(results)} agents completed successfully.\n\n" + "\n\n".join(
            summaries
        )

        return FanOutResult(results=results, combined_summary=combined)


async def _default_run_agent(
    *,
    goal: str,
    workspace_root: Path,
    run_id: str,
) -> str:
    """Default agent runner — runs beep agent as a subprocess."""
    import subprocess

    try:
        result = subprocess.run(
            ["beep", "agent", goal],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.stdout[:5000] + (result.stderr[:2000] if result.stderr else "")
    except subprocess.TimeoutExpired:
        return f"Agent {run_id} timed out after 5 minutes."
    except FileNotFoundError:
        return f"beep CLI not found for agent {run_id}."
