"""Portable agent bundle build and storage helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

from beep import __version__ as CLI_VERSION
from beep.agent.bundle_contract import (
    AgentBundleCompatibility,
    AgentBundleModelConfig,
    AgentBundleProvenance,
    AgentBundleRuntimeRequirements,
    AgentBundleToolPolicy,
    PortableAgentBundleManifest,
    validate_bundle_payload,
)
from beep.agent.provider_options import build_agent_provider_options
from beep.config import BeepConfig, CONFIG_DIR

AGENT_BUNDLE_LIBRARY_DIR = CONFIG_DIR / "agent-bundles"
BUNDLE_FILE_SUFFIX = ".beep-agent.json"
_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def bundle_file_name(agent_id: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", str(agent_id).strip()).strip("-").lower()
    if not normalized:
        normalized = "agent"
    return f"{normalized}{BUNDLE_FILE_SUFFIX}"


def default_bundle_output_path(agent_id: str) -> Path:
    return Path.cwd() / bundle_file_name(agent_id)


def default_bundle_library_path(agent_id: str) -> Path:
    return AGENT_BUNDLE_LIBRARY_DIR / bundle_file_name(agent_id)


def derive_agent_name(agent_id: str) -> str:
    words = str(agent_id).replace("_", " ").replace("-", " ").split()
    if not words:
        return "Portable Agent"
    return " ".join(word.capitalize() for word in words)


def build_bundle_from_config(
    config: BeepConfig,
    *,
    agent_id: str,
    name: str | None = None,
    description: str = "",
    system_prompt: str = "",
    tags: list[str] | None = None,
    created_by: str = "",
    source_repository: str = "",
    source_revision: str = "",
    runner_kinds: list[str] | None = None,
) -> PortableAgentBundleManifest:
    provider_key = str(config.agent_backend or "").strip()
    model_id = str(config.effective_agent_model or "").strip()
    if not provider_key:
        raise ValueError("Active autonomous-agent config must define agent_backend before export")
    if not model_id:
        raise ValueError("Active autonomous-agent config must define agent_model or default_model before export")

    normalized_tags = []
    for value in tags or []:
        text = str(value).strip()
        if text and text not in normalized_tags:
            normalized_tags.append(text)

    metadata: dict[str, object] = {}
    if config.project_id is not None:
        metadata["project_id"] = config.project_id

    manifest = PortableAgentBundleManifest(
        agent_id=str(agent_id).strip(),
        name=(name or derive_agent_name(agent_id)).strip(),
        description=description.strip(),
        system_prompt=system_prompt,
        model=AgentBundleModelConfig(
            provider_key=provider_key,
            base_url=config.effective_agent_base_url,
            model_id=model_id,
            temperature=float(config.temperature),
            max_tokens=int(config.max_tokens),
            provider_options=build_agent_provider_options(config) or {},
        ),
        tool_policy=AgentBundleToolPolicy(
            allow_mcp_tools=bool(config.mcp_enabled),
            allow_builtin_tools=True,
        ),
        mcp_server_ids=[server.name for server in config.mcp_servers] if config.mcp_enabled else [],
        tags=normalized_tags,
        metadata=metadata,
        compatibility=AgentBundleCompatibility(min_cli_version=CLI_VERSION),
        runtime=AgentBundleRuntimeRequirements(
            supported_runner_kinds=[value.strip() for value in (runner_kinds or ["local"]) if value.strip()],
        ),
        provenance=AgentBundleProvenance(
            created_at=_utc_now_iso(),
            created_by=created_by.strip(),
            source_repository=source_repository.strip(),
            source_revision=source_revision.strip(),
        ),
    )
    manifest.validate()
    return manifest


def load_bundle_manifest(path: Path) -> PortableAgentBundleManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Bundle file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Bundle file is not valid JSON: {path}") from exc
    return validate_bundle_payload(raw)


def resolve_bundle_manifest(reference: str | Path) -> tuple[PortableAgentBundleManifest, Path]:
    candidate_path = Path(reference)
    if candidate_path.exists():
        resolved = candidate_path.resolve()
        return load_bundle_manifest(resolved), resolved

    library_candidate = default_bundle_library_path(str(reference))
    if library_candidate.exists():
        resolved = library_candidate.resolve()
        return load_bundle_manifest(resolved), resolved

    raise ValueError(
        f"Bundle {reference!r} was not found as a file path or installed bundle ID under {AGENT_BUNDLE_LIBRARY_DIR}"
    )


def build_runtime_config_from_bundle(
    manifest: PortableAgentBundleManifest,
    *,
    base_config: BeepConfig,
    model_override: str | None = None,
) -> BeepConfig:
    runtime_config = base_config.model_copy(deep=True)
    runtime_config.agent_backend = manifest.model.provider_key
    runtime_config.agent_base_url = manifest.model.base_url or None
    runtime_config.agent_model = (model_override or manifest.model.model_id or "").strip() or None
    runtime_config.temperature = float(manifest.model.temperature)
    runtime_config.max_tokens = int(manifest.model.max_tokens)
    project_id = manifest.metadata.get("project_id")
    if isinstance(project_id, int):
        runtime_config.project_id = project_id
    return runtime_config


def write_bundle_manifest(
    manifest: PortableAgentBundleManifest,
    destination: Path,
    *,
    overwrite: bool = False,
) -> Path:
    manifest.validate()
    if destination.exists() and not overwrite:
        raise ValueError(f"Refusing to overwrite existing bundle file: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(manifest.to_json(), encoding="utf-8")
    return destination


def install_bundle_manifest(
    manifest: PortableAgentBundleManifest,
    *,
    destination: Path | None = None,
    overwrite: bool = False,
) -> Path:
    target = destination or default_bundle_library_path(manifest.agent_id)
    return write_bundle_manifest(manifest, target, overwrite=overwrite)
