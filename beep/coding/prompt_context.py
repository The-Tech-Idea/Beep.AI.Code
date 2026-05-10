"""Workspace prompt context shared by chat, ask, and agent flows."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from beep.chat.prompts import build_tool_list_section, get_system_prompt
from beep.memory.loader import load_project_memory
from beep.rules.resolver import build_rules_context


def _build_language_profile_section(workspace_path: Path) -> str:
    """Detect project languages and inject available commands into the prompt."""
    try:
        from beep.app_service import get_app_service

        registry = get_app_service().language_registry
        profile = registry.build_profile(str(workspace_path))
        section = profile.to_prompt_section()
        return section if section.strip() else ""
    except Exception:
        return ""


def _build_template_section(workspace_path: Path) -> str:
    """Detect matching project templates and inject guidance."""
    try:
        from beep.app_service import get_app_service

        registry = get_app_service().template_registry
        matches = registry.match_project(str(workspace_path))
        if not matches:
            return ""
        lines = ["## Detected Project Template"]
        best = matches[0]
        lines.append(f"Template: {best.full_name}")
        if best.description:
            lines.append(f"Description: {best.description}")
        if best.build_command:
            lines.append(f"Build: {best.build_command}")
        if best.test_command:
            lines.append(f"Test: {best.test_command}")
        if best.lint_command:
            lines.append(f"Lint: {best.lint_command}")
        if best.recommended_tools:
            lines.append(f"Recommended tools: {', '.join(best.recommended_tools)}")
        return "\n".join(lines)
    except Exception:
        return ""


def _build_agent_workflow_section(tools: list | None) -> str:
    """Describe only the coding-agent workflows supported by the active tool set."""
    if not tools:
        return ""

    tool_names = {str(getattr(tool, "name", "")) for tool in tools}
    if not tool_names:
        return ""

    lines = ["### Active Workflow Guidance", ""]

    if {"project_scaffold", "project_validate"} & tool_names:
        lines.append(
            "- Use `project_validate` to check if an existing project matches a known template. "
            "Use `project_scaffold` to create new projects from templates."
        )

    if {"code_snippet", "code_snippet_list"} & tool_names:
        lines.append(
            "- Use `code_snippet_list` to see available code snippet templates, then use `code_snippet` "
            "to generate individual code files (e.g., fastapi-route, react-component, python-class)."
        )

    if {"semantic_search", "find_related_code"} & tool_names:
        lines.append(
            "- Use `semantic_search` or `find_related_code` first for exploratory code discovery, then fall back to `search` for exact-string confirmation."
        )
    else:
        lines.append(
            "- Semantic retrieval is unavailable in this workspace, so use `glob_files`, `search`, `context`, and `file_read` for discovery."
        )

    lsp_tools = [
        name
        for name in (
            "python_hover",
            "python_definition",
            "python_references",
            "python_workspace_symbols",
            "python_rename",
            "csharp_symbols",
            "csharp_diagnostics",
            "csharp_dependencies",
            "javascript_symbols",
            "javascript_definitions",
            "typescript_symbols",
            "typescript_definitions",
        )
        if name in tool_names
    ]
    if lsp_tools:
        lines.append(
            "- Precise code-intelligence tools are available for symbol inspection and navigation: "
            + ", ".join(f"`{name}`" for name in lsp_tools)
            + "."
        )
        if "python_rename" in tool_names:
            lines.append(
                "- `python_rename` mutates files; use it only when a semantic rename is needed and expect an approval boundary before changes are applied."
            )
    else:
        lines.append(
            "- LSP-style symbol workflows are unavailable here, so do not assume hover, definition, references, workspace-symbol, or rename operations exist."
        )

    return "\n".join(lines)


def _build_standards_section() -> str:
    """Inject default coding standards into the agent prompt."""
    try:
        from beep.standards.defaults import DEFAULT_STANDARDS

        lines = ["## Default Engineering Standards", ""]
        lines.append(
            "You must produce code that follows Clean Code, SOLID, and the active architecture profile."
        )
        lines.append("")
        lines.append("Default rules:")

        all_rules: list[str] = []
        for std in DEFAULT_STANDARDS:
            all_rules.extend(std.rules)

        seen: set[str] = set()
        for rule in all_rules:
            if rule not in seen:
                lines.append(f"- {rule}")
                seen.add(rule)

        lines.append("")
        lines.append("When unsure:")
        lines.append("1. Inspect existing project structure.")
        lines.append("2. Follow existing conventions.")
        lines.append("3. Prefer minimal safe changes.")
        lines.append("4. Explain any architectural decision in the final response.")

        return "\n".join(lines)
    except Exception:
        return ""


def build_workspace_system_prompt(
    mode: str,
    workspace_root: Path | str,
    *,
    tools: list | None = None,
    extra_sections: Iterable[str] | None = None,
    skill_query: str | None = None,
    server_skills: list | None = None,
) -> str:
    """Build a system prompt enriched with project memory, active rules, and tool list."""
    workspace_path = Path(workspace_root)
    sections = [get_system_prompt(mode)]

    memory_prompt = load_project_memory(workspace_path).to_prompt_section().strip()
    if memory_prompt:
        sections.append(memory_prompt)

    try:
        from beep.rules.loader import load_rules

        rules, _errors = load_rules(workspace_path)
    except Exception:
        rules = []

    rules_context = build_rules_context(rules)
    if rules_context:
        sections.append(rules_context)

    if skill_query:
        try:
            from beep.skills.loader import load_skills, server_skills_to_definitions
            from beep.skills.resolver import SkillResolver

            local_skills, _serrors, _sroots = load_skills(workspace_path)
            all_skills = list(local_skills)
            if server_skills:
                all_skills.extend(server_skills_to_definitions(server_skills))
            if all_skills:
                resolver = SkillResolver(all_skills)
                matches = resolver.resolve(skill_query, max_skills=3, budget_chars=3000)
                if matches:
                    skill_lines = ["## Active Skills"]
                    for match in matches:
                        skill_lines.append(f"\n### {match.skill.name}\n{match.skill.body}")
                    sections.append("\n".join(skill_lines).strip())
        except Exception:
            pass

    if mode == "agent":
        standards_section = _build_standards_section()
        if standards_section:
            sections.append(standards_section)

    if tools:
        tool_section = build_tool_list_section(tools)
        if tool_section:
            sections.append(tool_section)
        if mode == "agent":
            workflow_section = _build_agent_workflow_section(tools)
            if workflow_section:
                sections.append(workflow_section)
            lang_section = _build_language_profile_section(workspace_path)
            if lang_section:
                sections.append(lang_section)
            tpl_section = _build_template_section(workspace_path)
            if tpl_section:
                sections.append(tpl_section)

    if extra_sections:
        sections.extend(section.strip() for section in extra_sections if section.strip())

    return "\n\n".join(sections)
