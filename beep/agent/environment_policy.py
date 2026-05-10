"""Compatibility and repair policy helpers for the managed agent runtime."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from beep.agent.environment_catalog import AgentPackage


def build_compatibility_stamp(
    *,
    packages: dict[str, AgentPackage],
    cli_version: str,
    metadata_version: int,
) -> dict[str, Any]:
    manifest = [
        {
            "key": package.key,
            "pip_name": package.pip_name,
            "import_name": package.import_name,
            "required": package.required,
        }
        for _, package in sorted(packages.items())
    ]
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "metadata_version": metadata_version,
        "cli_version": cli_version,
        "catalog_hash": digest[:16],
    }


def resolve_compatibility(
    *,
    config: dict[str, Any],
    env_exists: bool,
    missing: list[str],
    expected: dict[str, Any],
) -> dict[str, Any]:
    recorded = config.get("compatibility") if isinstance(config.get("compatibility"), dict) else None

    if not env_exists:
        return {
            "status": "not_created",
            "reason": "Managed agent environment has not been created yet.",
            "recorded": recorded,
            "expected": expected,
        }
    if missing:
        return {
            "status": "incomplete",
            "reason": "Managed agent environment is missing required packages.",
            "recorded": recorded,
            "expected": expected,
        }
    if recorded is None:
        return {
            "status": "stale",
            "reason": "Managed agent environment has no recorded compatibility stamp.",
            "recorded": None,
            "expected": expected,
        }

    mismatches: list[str] = []
    for key, expected_value in expected.items():
        recorded_value = recorded.get(key)
        if recorded_value != expected_value:
            mismatches.append(f"{key}={recorded_value!r} expected {expected_value!r}")

    if mismatches:
        return {
            "status": "stale",
            "reason": "Compatibility stamp mismatch: " + "; ".join(mismatches),
            "recorded": recorded,
            "expected": expected,
        }

    return {
        "status": "current",
        "reason": "Managed agent environment matches the current CLI compatibility stamp.",
        "recorded": recorded,
        "expected": expected,
    }


def resolve_repair_guidance(
    *,
    config: dict[str, Any],
    status: str,
    compatibility: dict[str, Any],
    missing: list[str],
) -> dict[str, Any]:
    compatibility_status = str(compatibility.get("status") or "unknown")
    recorded = compatibility.get("recorded")
    expected = compatibility.get("expected")
    recorded_status = str(config.get("status") or "")
    last_error = str(config.get("last_error") or "").strip()

    if status == "ready" and compatibility_status == "current":
        return {
            "action": "none",
            "command": None,
            "reason": "Managed agent runtime is current.",
        }

    if status == "not_created":
        return {
            "action": "setup",
            "command": "beep agent setup",
            "reason": "Managed agent environment does not exist yet.",
        }

    if recorded_status in {"creating", "error"} and (missing or last_error):
        return {
            "action": "reinstall",
            "command": "beep agent reinstall runtime",
            "reason": "Previous managed runtime setup did not complete cleanly; rebuild the managed runtime from scratch.",
        }

    if missing:
        return {
            "action": "setup",
            "command": "beep agent setup",
            "reason": "Managed agent environment is missing required packages.",
        }

    if compatibility_status == "stale":
        recorded_version = recorded.get("metadata_version") if isinstance(recorded, dict) else None
        expected_version = expected.get("metadata_version") if isinstance(expected, dict) else None
        if recorded_version is not None and expected_version is not None and recorded_version != expected_version:
            return {
                "action": "reinstall",
                "command": "beep agent reinstall runtime",
                "reason": "Managed runtime compatibility metadata changed; rebuild the managed runtime from scratch.",
            }
        return {
            "action": "setup",
            "command": "beep agent setup",
            "reason": "Managed runtime compatibility drift detected; refresh the managed runtime.",
        }

    return {
        "action": "setup",
        "command": "beep agent setup",
        "reason": "Managed agent runtime needs repair.",
    }