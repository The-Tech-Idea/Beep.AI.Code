from __future__ import annotations

from unittest.mock import AsyncMock


class HistoryFakeCompiledGraph:
    def __init__(self, result: dict[str, object]) -> None:
        self.ainvoke = AsyncMock(return_value=result)


class HistoryFakeStateGraph:
    def __init__(self, _state_type: object) -> None:
        self.compiled = HistoryFakeCompiledGraph(
            {
                "messages": [],
                "steps_executed": 1,
                "tool_calls_executed": 0,
                "files_touched": [],
                "run_reason": "completed",
                "final_message": "done",
                "consecutive_failure_steps": 0,
                "tool_call_hashes": {},
                "per_step_limit_hit": False,
                "total_limit_hit": False,
            }
        )

    def add_node(self, _name: str, _node: object) -> None:
        return None

    def add_edge(self, _start: object, _end: object) -> None:
        return None

    def add_conditional_edges(self, _name: str, _route: object, _mapping: dict[str, object]) -> None:
        return None

    def compile(self, *, checkpointer: object) -> HistoryFakeCompiledGraph:
        return self.compiled


class HistoryFakeAsyncSqliteSaverContext:
    async def __aenter__(self) -> HistoryFakeAsyncSqliteSaverContext:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class HistoryFakeAsyncSqliteSaver:
    @classmethod
    def from_conn_string(cls, conn_string: str) -> HistoryFakeAsyncSqliteSaverContext:
        return HistoryFakeAsyncSqliteSaverContext()


class HistoryFakeToolNode:
    def __init__(self, _tools: object) -> None:
        return None