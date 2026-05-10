"""Validation helpers for verified MCP tool contracts."""

from __future__ import annotations

from typing import Any

from beep.config import MCPToolConfig


def parse_verified_tool_contracts(payload: Any) -> list[MCPToolConfig]:
    """Validate and normalize verified MCP tool-contract payloads.

    Supported input shapes:
    - [{...tool...}, {...tool...}]
    - {"tools": [...tool...]}
    - {"result": {"tools": [...tool...]}}
    """
    raw_tools = _extract_raw_tools(payload)
    if not raw_tools:
        raise ValueError("Verified tool-contract payload must include at least one tool entry")

    parsed_tools: list[MCPToolConfig] = []
    seen_names: set[str] = set()
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict):
            raise ValueError("Each verified MCP tool entry must be a JSON object")
        name = str(raw_tool.get("name", "") or "").strip()
        if not name:
            raise ValueError("Verified MCP tool entries must include a non-empty name")
        if name in seen_names:
            raise ValueError(f"Verified MCP tool payload contains duplicate tool name '{name}'")
        seen_names.add(name)

        description = str(raw_tool.get("description", "") or "").strip()
        parameters = _extract_parameters(raw_tool)
        read_only_safe = _extract_read_only_safe(raw_tool)
        requires_human_approval = bool(raw_tool.get("requires_human_approval", True))
        parsed_tools.append(
            MCPToolConfig(
                name=name,
                description=description,
                parameters=parameters,
                read_only_safe=read_only_safe,
                requires_human_approval=requires_human_approval,
            )
        )

    return parsed_tools


def build_verified_tool_metadata(
    *,
    source: str,
    tools: list[MCPToolConfig],
    protocol_version: str | None = None,
    server_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build managed-definition metadata for a verified tool set."""
    metadata = {
        "verification_scope": "launch-and-tool-metadata",
        "tool_contracts_included": bool(tools),
        "tool_names": [tool.name for tool in tools],
        "verified_tool_contract_source": source,
    }
    if protocol_version:
        metadata["verified_tool_protocol_version"] = protocol_version
    if server_info:
        metadata["verified_tool_server_info"] = dict(server_info)
    return metadata


def _extract_raw_tools(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Verified tool-contract payload must be a JSON object or array")
    if isinstance(payload.get("tools"), list):
        return list(payload["tools"])
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("tools"), list):
        return list(result["tools"])
    raise ValueError("Verified tool-contract payload must include a 'tools' array")


def _extract_parameters(raw_tool: dict[str, Any]) -> dict[str, Any]:
    for key in ("inputSchema", "input_schema", "parameters"):
        value = raw_tool.get(key)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(f"Verified MCP tool '{raw_tool.get('name', '')}' has non-object {key}")
        return dict(value)
    return {}


def _extract_read_only_safe(raw_tool: dict[str, Any]) -> bool:
    value = raw_tool.get("read_only_safe")
    if value is not None:
        return bool(value)
    annotations = raw_tool.get("annotations")
    if isinstance(annotations, dict) and isinstance(annotations.get("readOnlyHint"), bool):
        return annotations["readOnlyHint"]
    return False


__all__ = ["build_verified_tool_metadata", "parse_verified_tool_contracts"]