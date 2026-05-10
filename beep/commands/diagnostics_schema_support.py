"""Schema inspection helpers for diagnostics and doctor commands."""

from __future__ import annotations

import json
from pathlib import Path


def inspect_config_schema(config_file: Path, *, expected_schema: int) -> dict[str, object]:
    if not config_file.exists():
        return {
            "status": "not_created",
            "schema_version": None,
            "reason": "Configuration file does not exist yet.",
        }

    try:
        payload = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "corrupt",
            "schema_version": None,
            "reason": "Configuration file could not be parsed.",
        }

    if not isinstance(payload, dict):
        return {
            "status": "corrupt",
            "schema_version": None,
            "reason": "Configuration file does not contain a JSON object.",
        }

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int):
        return {
            "status": "legacy",
            "schema_version": None,
            "reason": "Configuration file predates schema stamping and will be rewritten on load.",
        }
    if schema_version < expected_schema:
        return {
            "status": "legacy",
            "schema_version": schema_version,
            "reason": "Configuration file is older than the current CLI schema and will be migrated on load.",
        }
    if schema_version > expected_schema:
        return {
            "status": "unsupported",
            "schema_version": schema_version,
            "reason": "Configuration file was written by a newer CLI version.",
        }
    return {
        "status": "current",
        "schema_version": schema_version,
        "reason": "Configuration file matches the current CLI schema.",
    }


def inspect_session_history_schema(history_dir: Path, *, expected_schema: int) -> dict[str, object]:
    if not history_dir.exists():
        return {
            "status": "empty",
            "files": 0,
            "legacy_files": 0,
            "unsupported_files": 0,
            "corrupt_files": 0,
            "reason": "No local session history files found.",
        }

    files = sorted(history_dir.glob("*.jsonl"))
    if not files:
        return {
            "status": "empty",
            "files": 0,
            "legacy_files": 0,
            "unsupported_files": 0,
            "corrupt_files": 0,
            "reason": "No local session history files found.",
        }

    legacy = 0
    unsupported = 0
    corrupt = 0
    for path in files:
        try:
            first_nonempty = None
            with open(path, encoding="utf-8") as file_handle:
                for line in file_handle:
                    stripped = line.strip()
                    if stripped:
                        first_nonempty = stripped
                        break
        except OSError:
            corrupt += 1
            continue

        if first_nonempty is None:
            legacy += 1
            continue

        try:
            entry = json.loads(first_nonempty)
        except json.JSONDecodeError:
            corrupt += 1
            continue

        if not isinstance(entry, dict):
            corrupt += 1
            continue

        if entry.get("role") == "meta" and entry.get("kind") == "session_history_schema":
            version = entry.get("schema_version")
            if isinstance(version, int) and version <= expected_schema:
                continue
            unsupported += 1
            continue

        legacy += 1

    if unsupported:
        status = "unsupported"
        reason = f"{unsupported} session history file(s) require a newer CLI schema."
    elif corrupt:
        status = "corrupt"
        reason = f"{corrupt} session history file(s) could not be parsed."
    elif legacy:
        status = "legacy"
        reason = f"{legacy} legacy session history file(s) will migrate automatically when accessed."
    else:
        status = "current"
        reason = f"All {len(files)} session history file(s) match the current schema."

    return {
        "status": status,
        "files": len(files),
        "legacy_files": legacy,
        "unsupported_files": unsupported,
        "corrupt_files": corrupt,
        "reason": reason,
    }


def inspect_workspace_session_memory_schema(
    workspace: Path,
    *,
    expected_schema: int,
) -> dict[str, object]:
    memory_path = workspace / ".beep" / "session_memory.json"
    if not memory_path.exists():
        return {
            "status": "absent",
            "schema_version": None,
            "path": memory_path,
            "reason": "Workspace session memory has not been created yet.",
        }

    try:
        payload = json.loads(memory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "corrupt",
            "schema_version": None,
            "path": memory_path,
            "reason": "Workspace session memory could not be parsed.",
        }

    if not isinstance(payload, dict):
        return {
            "status": "corrupt",
            "schema_version": None,
            "path": memory_path,
            "reason": "Workspace session memory does not contain a JSON object.",
        }

    schema_version = payload.get("schema_version")
    if schema_version is None:
        return {
            "status": "legacy",
            "schema_version": None,
            "path": memory_path,
            "reason": "Workspace session memory predates schema stamping and will be rewritten on load.",
        }
    if not isinstance(schema_version, int):
        return {
            "status": "corrupt",
            "schema_version": None,
            "path": memory_path,
            "reason": "Workspace session memory schema marker is invalid.",
        }
    if schema_version < expected_schema:
        return {
            "status": "legacy",
            "schema_version": schema_version,
            "path": memory_path,
            "reason": "Workspace session memory is older than the current CLI schema and will be migrated on load.",
        }
    if schema_version > expected_schema:
        return {
            "status": "unsupported",
            "schema_version": schema_version,
            "path": memory_path,
            "reason": "Workspace session memory was written by a newer CLI version.",
        }

    facts = payload.get("facts")
    if not isinstance(facts, dict):
        return {
            "status": "corrupt",
            "schema_version": schema_version,
            "path": memory_path,
            "reason": "Workspace session memory payload is missing the facts object.",
        }
    return {
        "status": "current",
        "schema_version": schema_version,
        "path": memory_path,
        "reason": "Workspace session memory matches the current schema.",
    }


def build_repair_guidance(
    *,
    config: object,
    config_schema: dict[str, object],
    agent_runtime: dict[str, object],
    history_schema: dict[str, object],
    session_memory_schema: dict[str, object],
) -> list[str]:
    guidance: list[str] = []

    if not bool(getattr(config, "is_configured", False)):
        guidance.append("Run `beep setup` to configure server access before using chat or agent commands.")

    repair_command = agent_runtime.get("repair_command")
    repair_reason = agent_runtime.get("repair_reason")
    if repair_command:
        guidance.append(f"Run `{repair_command}`. {repair_reason}")

    if config_schema.get("status") == "unsupported":
        version = config_schema.get("schema_version")
        guidance.append(
            f"Upgrade Beep.AI.Code before using the existing config file; it was written with schema version {version}."
        )
    elif config_schema.get("status") == "corrupt":
        guidance.append("Repair or recreate `~/.beepai/code.json`; `beep setup` can rewrite a valid config file.")

    if history_schema.get("status") == "legacy":
        guidance.append("Legacy local session histories will migrate automatically the next time they are loaded, listed, or searched.")
    elif history_schema.get("status") == "unsupported":
        guidance.append("Upgrade Beep.AI.Code before loading local session history files written by a newer CLI version.")
    elif history_schema.get("status") == "corrupt":
        guidance.append("Back up or remove unreadable files under `~/.beepai/history` to clear corrupt local session history.")

    if session_memory_schema.get("status") == "legacy":
        guidance.append("Legacy workspace session memory will migrate automatically the next time the agent memory is loaded.")
    elif session_memory_schema.get("status") == "unsupported":
        guidance.append("Upgrade Beep.AI.Code before loading workspace session memory written by a newer CLI version.")
    elif session_memory_schema.get("status") == "corrupt":
        guidance.append(
            f"Delete `{session_memory_schema.get('path')}` to reset corrupt workspace session memory."
        )

    if not guidance:
        guidance.append("No repair actions recommended. After CLI upgrades, rerun `beep doctor` or `beep diagnostics`.")

    return guidance