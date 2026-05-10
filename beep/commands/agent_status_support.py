"""Status and rendering helpers for autonomous agent admin commands."""

from __future__ import annotations

from collections.abc import Callable

from rich.table import Table

from beep.agent.environment import AgentEnvironmentManager
from beep.agent.provider_options import describe_agent_provider_options
from beep.agent.provider_capabilities import build_provider_descriptor
from beep.agent.provider_plugins import (
    describe_agent_provider_guidance,
    is_agent_backend_configured,
)
from beep.config import BeepConfig
from beep.runtime.workspace_intelligence import (
    WorkspaceIntelligenceStatusReport,
    build_semantic_search_status_report,
    build_workspace_intelligence_capabilities,
)
from beep.utils.console import get_console


def _format_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{size_bytes} B"


def render_agent_env_status(status: dict[str, object]) -> None:
    table = Table(title="Agent Runtime Environment")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Status", str(status.get("status", "unknown")))
    table.add_row("Compatibility", str(status.get("compatibility_status", "unknown")))
    table.add_row("Repair Command", str(status.get("repair_command") or "None"))
    table.add_row("Environment", str(status.get("env_path", "")))
    table.add_row("Python", str(status.get("python_exe", "")))
    table.add_row("Size", _format_size(int(status.get("size_bytes", 0) or 0)))
    missing = status.get("missing", []) or []
    table.add_row(
        "Missing Required", ", ".join(str(item) for item in missing) if missing else "None"
    )
    compatibility_reason = status.get("compatibility_reason")
    table.add_row("Compatibility Note", str(compatibility_reason or "None"))
    repair_reason = status.get("repair_reason")
    table.add_row("Repair Note", str(repair_reason or "None"))
    last_error = status.get("last_error")
    table.add_row("Last Error", str(last_error or "None"))
    get_console().print(table)

    package_table = Table(title="Managed Packages")
    package_table.add_column("Package", style="cyan")
    package_table.add_column("Required")
    package_table.add_column("Installed")
    package_table.add_column("Pip Name", overflow="fold")
    packages = status.get("packages", {})
    if isinstance(packages, dict):
        for key in sorted(packages):
            package = packages[key]
            if not isinstance(package, dict):
                continue
            package_table.add_row(
                str(package.get("name", key)),
                "Yes" if package.get("required") else "No",
                "Yes" if package.get("installed") else "No",
                str(package.get("pip_name", "")),
            )
    get_console().print(package_table)


def _coerce_workspace_intelligence_status_report(
    report: object,
) -> WorkspaceIntelligenceStatusReport | None:
    if isinstance(report, WorkspaceIntelligenceStatusReport):
        return report
    if isinstance(report, dict):
        return build_semantic_search_status_report(report)
    return None


def render_workspace_intelligence_reports(reports: list[object] | None) -> None:
    if not reports:
        return

    for raw_report in reports:
        report = _coerce_workspace_intelligence_status_report(raw_report)
        if report is None:
            continue
        table = Table(title=report.title)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        for row in report.rows:
            table.add_row(str(row.label), str(row.value))
        get_console().print(table)


def render_provider_status(config: BeepConfig, *, plugin_registry: object | None = None) -> None:
    descriptor = build_provider_descriptor(config, plugin_registry=plugin_registry)
    guidance = describe_agent_provider_guidance(config, plugin_registry=plugin_registry)
    base_url = (
        config.agent_base_url.rstrip("/")
        if config.agent_base_url
        else guidance.default_base_url or config.effective_agent_base_url or "None"
    )
    table = Table(title="Agent Provider")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Backend", descriptor.display_name)
    table.add_row("Provider Key", descriptor.key)
    table.add_row("Source", guidance.source)
    table.add_row(
        "Configured",
        "Yes" if is_agent_backend_configured(config, plugin_registry=plugin_registry) else "No",
    )
    table.add_row("Base URL", base_url)
    table.add_row("Model", str(config.effective_agent_model or "None"))
    for label, value in describe_agent_provider_options(config):
        table.add_row(label, value)
    get_console().print(table)


def render_provider_guidance(config: BeepConfig, *, plugin_registry: object | None = None) -> None:
    guidance = describe_agent_provider_guidance(config, plugin_registry=plugin_registry)
    table = Table(title="Provider Guidance")
    table.add_column("Property", style="cyan")
    table.add_column("Value", overflow="fold")
    table.add_row("Selected Provider", guidance.display_name)
    table.add_row("Source", guidance.source)
    table.add_row(
        "Requires API Key",
        "Yes"
        if guidance.requires_api_key
        else "No"
        if guidance.requires_api_key is not None
        else "Unknown",
    )
    table.add_row(
        "Requires Model",
        "Yes"
        if guidance.requires_model
        else "No"
        if guidance.requires_model is not None
        else "Unknown",
    )
    table.add_row("Default Base URL", guidance.default_base_url or "None")
    table.add_row("Local Runtime", "Yes" if guidance.local_runtime else "No")
    if guidance.notes:
        table.add_row("Notes", "\n".join(f"- {note}" for note in guidance.notes))
    get_console().print(table)


def render_provider_capabilities(
    config: BeepConfig, *, plugin_registry: object | None = None
) -> None:
    capabilities = build_provider_descriptor(config, plugin_registry=plugin_registry).capabilities
    table = Table(title="Provider Capabilities")
    table.add_column("Capability", style="cyan")
    table.add_column("Exists")
    table.add_column("Notes", overflow="fold")
    for label, flag in [
        ("Chat Completion", capabilities.chat_completion),
        ("Tool Calling", capabilities.tool_calling),
        ("Streaming", capabilities.streaming),
        ("Structured Output", capabilities.structured_output),
        ("Vision", capabilities.vision),
        ("Embeddings", capabilities.embeddings),
        ("Local Runtime", capabilities.local_model_runtime),
    ]:
        table.add_row(label, "Yes" if flag.exists else "No", str(flag.notes or "None"))
    get_console().print(table)


def render_workspace_intelligence_capabilities(capabilities: object | None) -> None:
    if capabilities is None:
        return

    semantic = getattr(capabilities, "semantic_search", None)
    lsp = getattr(capabilities, "lsp", None)
    table = Table(title="Workspace Intelligence Capabilities")
    table.add_column("Capability", style="cyan")
    table.add_column("Exists")
    table.add_column("Notes", overflow="fold")

    rows = []
    if semantic is not None:
        rows.extend(
            [
                ("Semantic Search", semantic.semantic_search),
                ("Find Related", semantic.find_related),
                ("Local Indexing", semantic.local_indexing),
                ("Remote Git Indexing", semantic.remote_git_indexing),
                ("Hybrid Mode", semantic.hybrid_mode),
                ("Semantic Mode", semantic.semantic_mode),
                ("BM25 Mode", semantic.bm25_mode),
                ("Language Filters", semantic.language_filters),
                ("Path Filters", semantic.path_filters),
                ("Index Stats", semantic.index_stats),
            ]
        )
    if lsp is not None:
        rows.extend(
            [
                ("LSP Diagnostics", lsp.diagnostics),
                ("LSP Hover", lsp.hover),
                ("LSP Definition", lsp.definition),
                ("LSP References", lsp.references),
                ("LSP Rename", lsp.rename),
                ("LSP Workspace Symbols", lsp.workspace_symbols),
                ("LSP Code Actions", lsp.code_actions),
                ("LSP Formatting", lsp.formatting),
            ]
        )

    for label, flag in rows:
        table.add_row(
            label,
            "Yes" if getattr(flag, "exists", False) else "No",
            str(getattr(flag, "notes", "") or "None"),
        )
    get_console().print(table)


def get_workspace_intelligence_status(
    manager: AgentEnvironmentManager,
    status: dict[str, object],
    *,
    workspace_runtime_loader: Callable[[], object],
) -> tuple[list[object], object]:
    report: dict[str, object] = {
        "available": False,
        "workspace_root": None,
        "cached": False,
        "cached_root": None,
        "stats": None,
        "error": None,
    }
    if status.get("status") != "ready":
        report["error"] = (
            'Agent environment not ready. Run "beep agent setup" to enable managed workspace intelligence support.'
        )
        return [
            build_semantic_search_status_report(report)
        ], build_workspace_intelligence_capabilities(report)

    try:
        manager.inject_into_sys_path()
        runtime = workspace_runtime_loader()
        plugin_runtime = getattr(runtime, "plugin_runtime", None)
        registry = getattr(plugin_runtime, "registry", None)
        get_reports = getattr(registry, "get_workspace_intelligence_reports", None)
        if callable(get_reports):
            reports = get_reports(getattr(runtime, "workspace_root", None))
            if isinstance(reports, list):
                normalized_reports = [
                    item
                    for item in (
                        _coerce_workspace_intelligence_status_report(report) for report in reports
                    )
                    if item is not None
                ]
                if normalized_reports:
                    return normalized_reports, runtime.workspace_intelligence_capabilities
        adapter = runtime.semantic_search_adapter
        if adapter is None or not hasattr(adapter, "availability_report"):
            report["error"] = (
                "No semantic-search adapter is registered for the current workspace runtime."
            )
            return [
                build_semantic_search_status_report(report)
            ], runtime.workspace_intelligence_capabilities
        return [
            build_semantic_search_status_report(adapter.availability_report())
        ], runtime.workspace_intelligence_capabilities
    except Exception as exc:
        report["error"] = str(exc)
        return [
            build_semantic_search_status_report(report)
        ], build_workspace_intelligence_capabilities(report)
