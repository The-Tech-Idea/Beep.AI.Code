"""Managed package catalog for the dedicated agent runtime environment."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPackage:
    """Package metadata for the managed agent runtime environment."""

    key: str
    name: str
    pip_name: str
    import_name: str
    description: str
    required: bool = True


AGENT_PACKAGES: dict[str, AgentPackage] = {
    "langgraph": AgentPackage(
        key="langgraph",
        name="LangGraph",
        pip_name="langgraph>=0.4",
        import_name="langgraph",
        description="StateGraph runtime for durable agent workflows",
        required=True,
    ),
    "langchain_core": AgentPackage(
        key="langchain_core",
        name="LangChain Core",
        pip_name="langchain-core>=0.3",
        import_name="langchain_core",
        description="Core message, model, and tool primitives for LangGraph",
        required=True,
    ),
    "langgraph_checkpoint_sqlite": AgentPackage(
        key="langgraph_checkpoint_sqlite",
        name="LangGraph SQLite Checkpoint",
        pip_name="langgraph-checkpoint-sqlite>=2.0",
        import_name="langgraph.checkpoint.sqlite",
        description="Durable SQLite checkpointer used for agent resume",
        required=True,
    ),
    "pydantic": AgentPackage(
        key="pydantic",
        name="Pydantic",
        pip_name="pydantic>=2.0",
        import_name="pydantic",
        description="Typed schemas for agent state and tool argument models",
        required=True,
    ),
    "semble": AgentPackage(
        key="semble",
        name="Semble",
        pip_name="semble>=0.1.1",
        import_name="semble",
        description="Semantic code search for the autonomous coding agent",
        required=True,
    ),
    "jedi": AgentPackage(
        key="jedi",
        name="Jedi",
        pip_name="jedi>=0.19",
        import_name="jedi",
        description="Python code intelligence for hover, definitions, references, rename, and workspace symbols",
        required=True,
    ),
    "langsmith": AgentPackage(
        key="langsmith",
        name="LangSmith",
        pip_name="langsmith",
        import_name="langsmith",
        description="Optional tracing integration for agent runs",
        required=False,
    ),
    "tiktoken": AgentPackage(
        key="tiktoken",
        name="Tiktoken",
        pip_name="tiktoken",
        import_name="tiktoken",
        description="Token counting for accurate context window management",
        required=False,
    ),
}
