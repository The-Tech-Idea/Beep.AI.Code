"""Shared release metadata for package and deployment adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any, Mapping

from beep.agent.bundle_contract import PortableAgentBundleManifest

_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9]+")


def build_distribution_name(agent_id: str) -> str:
    normalized = _SLUG_PATTERN.sub("-", str(agent_id).strip().lower()).strip("-")
    return f"beep-agent-{normalized or 'agent'}"


@dataclass(frozen=True)
class SharedReleaseCompatibility:
    min_cli_version: str
    max_cli_version: str
    server_contract_versions: tuple[str, ...]
    sdk_contract_versions: tuple[str, ...]


@dataclass(frozen=True)
class SharedReleaseSignature:
    status: str
    algorithm: str
    key_id: str
    digest_sha256: str
    signed_at: str


@dataclass(frozen=True)
class SharedReleaseProvenance:
    created_at: str
    created_by: str
    publisher: str
    authoring_tool: str
    authoring_tool_version: str
    source_repository: str
    source_revision: str
    channel_annotations: dict[str, str]
    signature: SharedReleaseSignature | None = None


@dataclass(frozen=True)
class SharedReleaseMetadata:
    agent_id: str
    agent_name: str
    description: str
    distribution_name: str
    release_name: str
    tag_name: str
    bundle_file: str
    bundle_version: str
    bundle_schema_version: int
    runner_kinds: tuple[str, ...]
    compatibility: SharedReleaseCompatibility
    provenance: SharedReleaseProvenance

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["runner_kinds"] = list(self.runner_kinds)
        compatibility = payload.get("compatibility")
        if isinstance(compatibility, dict):
            compatibility["server_contract_versions"] = list(self.compatibility.server_contract_versions)
            compatibility["sdk_contract_versions"] = list(self.compatibility.sdk_contract_versions)
        provenance = payload.get("provenance")
        if isinstance(provenance, dict) and provenance.get("signature") is None:
            provenance.pop("signature", None)
        return payload


def build_shared_release_metadata(
    manifest: PortableAgentBundleManifest,
    *,
    distribution_name: str,
    bundle_file: str,
    description: str,
) -> SharedReleaseMetadata:
    signature = manifest.provenance.signature
    return SharedReleaseMetadata(
        agent_id=manifest.agent_id,
        agent_name=manifest.name,
        description=description,
        distribution_name=distribution_name,
        release_name=f"{manifest.name} v{manifest.bundle_version}",
        tag_name=f"{distribution_name}-v{manifest.bundle_version}",
        bundle_file=bundle_file,
        bundle_version=manifest.bundle_version,
        bundle_schema_version=manifest.schema_version,
        runner_kinds=tuple(manifest.runtime.supported_runner_kinds),
        compatibility=SharedReleaseCompatibility(
            min_cli_version=manifest.compatibility.min_cli_version,
            max_cli_version=manifest.compatibility.max_cli_version,
            server_contract_versions=tuple(manifest.compatibility.server_contract_versions),
            sdk_contract_versions=tuple(manifest.compatibility.sdk_contract_versions),
        ),
        provenance=SharedReleaseProvenance(
            created_at=manifest.provenance.created_at,
            created_by=manifest.provenance.created_by,
            publisher=manifest.provenance.publisher,
            authoring_tool=manifest.provenance.authoring_tool,
            authoring_tool_version=manifest.provenance.authoring_tool_version,
            source_repository=manifest.provenance.source_repository,
            source_revision=manifest.provenance.source_revision,
            channel_annotations=dict(manifest.provenance.channel_annotations),
            signature=(
                SharedReleaseSignature(
                    status=signature.status,
                    algorithm=signature.algorithm,
                    key_id=signature.key_id,
                    digest_sha256=signature.digest_sha256,
                    signed_at=signature.signed_at,
                )
                if signature is not None
                else None
            ),
        ),
    )


def build_channel_release_metadata_payload(
    shared_release_metadata: SharedReleaseMetadata,
    *,
    channel: str,
    output_kind: str,
    channel_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "channel": str(channel).strip().lower(),
        "output_kind": str(output_kind).strip(),
        "shared_release_metadata": shared_release_metadata.to_dict(),
        "channel_metadata": dict(channel_metadata),
    }


def render_channel_release_metadata_json(
    shared_release_metadata: SharedReleaseMetadata,
    *,
    channel: str,
    output_kind: str,
    channel_metadata: Mapping[str, Any],
) -> str:
    payload = build_channel_release_metadata_payload(
        shared_release_metadata,
        channel=channel,
        output_kind=output_kind,
        channel_metadata=channel_metadata,
    )
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = [
    "SharedReleaseMetadata",
    "build_channel_release_metadata_payload",
    "build_distribution_name",
    "build_shared_release_metadata",
    "render_channel_release_metadata_json",
]