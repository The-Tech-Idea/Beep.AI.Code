"""Portable agent bundle contract and compatibility helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import PurePosixPath
import re
from typing import Any

from beep import __version__ as CLI_VERSION

BUNDLE_KIND = "beep-agent-bundle"
BUNDLE_SCHEMA_VERSION = 1
_ASSET_DISPOSITIONS = frozenset({"embedded", "referenced", "generated"})
_SIGNATURE_STATUSES = frozenset({"placeholder", "signed"})
_SEMVER_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")


def _coerce_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _coerce_string_map(values: object) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in values.items():
        key_text = str(key).strip()
        value_text = str(value).strip()
        if key_text and value_text:
            result[key_text] = value_text
    return result


def _coerce_any_map(values: object) -> dict[str, Any]:
    return dict(values) if isinstance(values, dict) else {}


def _parse_semver(value: str, field_name: str) -> tuple[int, int, int]:
    match = _SEMVER_PATTERN.match(value.strip())
    if match is None:
        raise ValueError(f"{field_name} must use semver-like format MAJOR.MINOR.PATCH: {value}")
    return tuple(int(part) for part in match.groups())


def _validate_iso8601(value: str, field_name: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must use ISO-8601 date-time format: {value}") from exc


@dataclass
class AgentBundleToolPolicy:
    allowed_categories: list[str] = field(default_factory=list)
    blocked_tools: list[str] = field(default_factory=list)
    allow_mcp_tools: bool = True
    allow_builtin_tools: bool = True
    max_tool_calls_per_turn: int = 10

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleToolPolicy":
        mapping = _coerce_any_map(data)
        return cls(
            allowed_categories=_coerce_string_list(mapping.get("allowed_categories")),
            blocked_tools=_coerce_string_list(mapping.get("blocked_tools")),
            allow_mcp_tools=bool(mapping.get("allow_mcp_tools", True)),
            allow_builtin_tools=bool(mapping.get("allow_builtin_tools", True)),
            max_tool_calls_per_turn=int(mapping.get("max_tool_calls_per_turn", 10) or 10),
        )


@dataclass
class AgentBundleModelConfig:
    provider_key: str = ""
    base_url: str = ""
    model_id: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)
    provider_options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleModelConfig":
        mapping = _coerce_any_map(data)
        return cls(
            provider_key=str(mapping.get("provider_key", "") or "").strip(),
            base_url=str(mapping.get("base_url", "") or "").strip(),
            model_id=str(mapping.get("model_id", "") or "").strip(),
            temperature=float(mapping.get("temperature", 0.7)),
            max_tokens=int(mapping.get("max_tokens", 4096) or 4096),
            top_p=float(mapping.get("top_p", 1.0)),
            stop_sequences=_coerce_string_list(mapping.get("stop_sequences")),
            provider_options=_coerce_any_map(mapping.get("provider_options")),
        )


@dataclass
class AgentBundleCompatibility:
    min_cli_version: str = CLI_VERSION
    max_cli_version: str = ""
    server_contract_versions: list[str] = field(default_factory=list)
    sdk_contract_versions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleCompatibility":
        mapping = _coerce_any_map(data)
        return cls(
            min_cli_version=str(mapping.get("min_cli_version", CLI_VERSION) or CLI_VERSION).strip(),
            max_cli_version=str(mapping.get("max_cli_version", "") or "").strip(),
            server_contract_versions=_coerce_string_list(mapping.get("server_contract_versions")),
            sdk_contract_versions=_coerce_string_list(mapping.get("sdk_contract_versions")),
        )

    def validate(self) -> None:
        _parse_semver(self.min_cli_version, "compatibility.min_cli_version")
        if self.max_cli_version:
            minimum = _parse_semver(self.min_cli_version, "compatibility.min_cli_version")
            maximum = _parse_semver(self.max_cli_version, "compatibility.max_cli_version")
            if maximum < minimum:
                raise ValueError("compatibility.max_cli_version must be greater than or equal to min_cli_version")


@dataclass
class AgentBundleRuntimeRequirements:
    python: str = ">=3.11"
    managed_agent_runtime: bool = True
    supported_runner_kinds: list[str] = field(default_factory=lambda: ["local"])
    required_capabilities: list[str] = field(default_factory=list)
    optional_capabilities: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleRuntimeRequirements":
        mapping = _coerce_any_map(data)
        return cls(
            python=str(mapping.get("python", ">=3.11") or ">=3.11").strip(),
            managed_agent_runtime=bool(mapping.get("managed_agent_runtime", True)),
            supported_runner_kinds=_coerce_string_list(mapping.get("supported_runner_kinds")) or ["local"],
            required_capabilities=_coerce_string_list(mapping.get("required_capabilities")),
            optional_capabilities=_coerce_string_list(mapping.get("optional_capabilities")),
        )

    def validate(self) -> None:
        if not self.python:
            raise ValueError("runtime.python must be non-empty")
        if not self.supported_runner_kinds:
            raise ValueError("runtime.supported_runner_kinds must include at least one runner kind")


@dataclass
class AgentBundleAsset:
    key: str
    kind: str = "text"
    disposition: str = "embedded"
    path: str = ""
    content: str | None = None
    media_type: str = "text/plain"
    generated_from: str = ""
    sha256: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleAsset":
        mapping = _coerce_any_map(data)
        return cls(
            key=str(mapping.get("key", "") or "").strip(),
            kind=str(mapping.get("kind", "text") or "text").strip(),
            disposition=str(mapping.get("disposition", "embedded") or "embedded").strip().lower(),
            path=str(mapping.get("path", "") or "").strip(),
            content=mapping.get("content") if isinstance(mapping.get("content"), str) else None,
            media_type=str(mapping.get("media_type", "text/plain") or "text/plain").strip(),
            generated_from=str(mapping.get("generated_from", "") or "").strip(),
            sha256=str(mapping.get("sha256", "") or "").strip(),
            metadata=_coerce_any_map(mapping.get("metadata")),
        )

    def validate(self) -> None:
        if not self.key:
            raise ValueError("bundle assets must have a non-empty key")
        if self.disposition not in _ASSET_DISPOSITIONS:
            raise ValueError(f"bundle asset {self.key!r} has unsupported disposition {self.disposition!r}")
        if self.disposition == "embedded" and self.content is None:
            raise ValueError(f"embedded asset {self.key!r} must include inline content")
        if self.disposition == "referenced":
            if not self.path:
                raise ValueError(f"referenced asset {self.key!r} must include a relative path")
            if "\\" in self.path:
                raise ValueError(f"referenced asset {self.key!r} must use '/' separators")
            pure_path = PurePosixPath(self.path)
            if pure_path.is_absolute() or any(part == ".." for part in pure_path.parts):
                raise ValueError(f"referenced asset {self.key!r} must stay inside the bundle root")
        if self.disposition == "generated" and not self.generated_from:
            raise ValueError(f"generated asset {self.key!r} must describe its generation source")


@dataclass
class AgentBundleSignature:
    status: str = "placeholder"
    algorithm: str = ""
    key_id: str = ""
    digest_sha256: str = ""
    signature: str = ""
    signed_at: str = ""

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleSignature":
        mapping = _coerce_any_map(data)
        return cls(
            status=str(mapping.get("status", "placeholder") or "placeholder").strip().lower(),
            algorithm=str(mapping.get("algorithm", "") or "").strip(),
            key_id=str(mapping.get("key_id", "") or "").strip(),
            digest_sha256=str(mapping.get("digest_sha256", "") or "").strip(),
            signature=str(mapping.get("signature", "") or "").strip(),
            signed_at=str(mapping.get("signed_at", "") or "").strip(),
        )

    def validate(self) -> None:
        if self.status not in _SIGNATURE_STATUSES:
            raise ValueError(
                "provenance.signature.status must be one of: " + ", ".join(sorted(_SIGNATURE_STATUSES))
            )
        if self.signed_at:
            _validate_iso8601(self.signed_at, "provenance.signature.signed_at")
        if self.signature and self.status != "signed":
            raise ValueError("provenance.signature.status must be 'signed' when signature content is present")
        if self.status == "signed" and (not self.algorithm or not self.signature):
            raise ValueError("signed provenance.signature entries must include both algorithm and signature")


@dataclass
class AgentBundleProvenance:
    created_at: str = ""
    created_by: str = ""
    authoring_tool: str = "beep-ai-code"
    authoring_tool_version: str = CLI_VERSION
    source_repository: str = ""
    source_revision: str = ""
    publisher: str = ""
    channel_annotations: dict[str, str] = field(default_factory=dict)
    signature: AgentBundleSignature | None = None

    @classmethod
    def from_dict(cls, data: object) -> "AgentBundleProvenance":
        mapping = _coerce_any_map(data)
        signature_data = mapping.get("signature")
        if signature_data is not None and not isinstance(signature_data, dict):
            raise ValueError("provenance.signature must be an object when provided")
        return cls(
            created_at=str(mapping.get("created_at", "") or "").strip(),
            created_by=str(mapping.get("created_by", "") or "").strip(),
            authoring_tool=str(mapping.get("authoring_tool", "beep-ai-code") or "beep-ai-code").strip(),
            authoring_tool_version=str(mapping.get("authoring_tool_version", CLI_VERSION) or CLI_VERSION).strip(),
            source_repository=str(mapping.get("source_repository", "") or "").strip(),
            source_revision=str(mapping.get("source_revision", "") or "").strip(),
            publisher=str(mapping.get("publisher", "") or "").strip(),
            channel_annotations=_coerce_string_map(mapping.get("channel_annotations")),
            signature=AgentBundleSignature.from_dict(signature_data) if isinstance(signature_data, dict) else None,
        )

    def validate(self) -> None:
        if self.created_at:
            _validate_iso8601(self.created_at, "provenance.created_at")
        _parse_semver(self.authoring_tool_version, "provenance.authoring_tool_version")
        if self.signature is not None:
            self.signature.validate()


@dataclass(frozen=True)
class AgentBundleCompatibilityReport:
    compatible: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass
class PortableAgentBundleManifest:
    agent_id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    framework: str = "langgraph"
    bundle_version: str = "1.0.0"
    kind: str = BUNDLE_KIND
    schema_version: int = BUNDLE_SCHEMA_VERSION
    model: AgentBundleModelConfig = field(default_factory=AgentBundleModelConfig)
    tool_policy: AgentBundleToolPolicy = field(default_factory=AgentBundleToolPolicy)
    mcp_server_ids: list[str] = field(default_factory=list)
    data_source_ids: list[str] = field(default_factory=list)
    guardrails_profile: str = "balanced"
    template_id: str = ""
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    assets: list[AgentBundleAsset] = field(default_factory=list)
    compatibility: AgentBundleCompatibility = field(default_factory=AgentBundleCompatibility)
    runtime: AgentBundleRuntimeRequirements = field(default_factory=AgentBundleRuntimeRequirements)
    provenance: AgentBundleProvenance = field(default_factory=AgentBundleProvenance)

    @classmethod
    def from_dict(cls, data: object) -> "PortableAgentBundleManifest":
        mapping = _coerce_any_map(data)
        return cls(
            agent_id=str(mapping.get("agent_id", mapping.get("id", "")) or "").strip(),
            name=str(mapping.get("name", "") or "").strip(),
            description=str(mapping.get("description", "") or "").strip(),
            system_prompt=str(mapping.get("system_prompt", "") or "").strip(),
            framework=str(mapping.get("framework", "langgraph") or "langgraph").strip().lower(),
            bundle_version=str(mapping.get("bundle_version", "1.0.0") or "1.0.0").strip(),
            kind=str(mapping.get("kind", BUNDLE_KIND) or BUNDLE_KIND).strip(),
            schema_version=int(mapping.get("schema_version", BUNDLE_SCHEMA_VERSION) or BUNDLE_SCHEMA_VERSION),
            model=AgentBundleModelConfig.from_dict(mapping.get("model")),
            tool_policy=AgentBundleToolPolicy.from_dict(mapping.get("tool_policy")),
            mcp_server_ids=_coerce_string_list(mapping.get("mcp_server_ids")),
            data_source_ids=_coerce_string_list(mapping.get("data_source_ids")),
            guardrails_profile=str(mapping.get("guardrails_profile", "balanced") or "balanced").strip().lower(),
            template_id=str(mapping.get("template_id", "") or "").strip(),
            enabled=bool(mapping.get("enabled", True)),
            tags=_coerce_string_list(mapping.get("tags")),
            metadata=_coerce_any_map(mapping.get("metadata")),
            assets=[AgentBundleAsset.from_dict(asset) for asset in mapping.get("assets", []) if isinstance(asset, dict)],
            compatibility=AgentBundleCompatibility.from_dict(mapping.get("compatibility")),
            runtime=AgentBundleRuntimeRequirements.from_dict(mapping.get("runtime")),
            provenance=AgentBundleProvenance.from_dict(mapping.get("provenance")),
        )

    def validate(self) -> None:
        if not self.agent_id:
            raise ValueError("agent bundles must define a non-empty agent_id")
        if not self.name:
            raise ValueError("agent bundles must define a non-empty name")
        if self.kind != BUNDLE_KIND:
            raise ValueError(f"agent bundle kind must be {BUNDLE_KIND!r}: {self.kind!r}")
        if self.schema_version < 1:
            raise ValueError("agent bundle schema_version must be >= 1")
        _parse_semver(self.bundle_version, "bundle_version")
        self.compatibility.validate()
        self.runtime.validate()
        self.provenance.validate()
        for asset in self.assets:
            asset.validate()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        provenance = payload.get("provenance")
        if isinstance(provenance, dict) and provenance.get("signature") is None:
            provenance.pop("signature", None)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def validate_bundle_payload(data: object) -> PortableAgentBundleManifest:
    if not isinstance(data, dict):
        raise ValueError("bundle payload must be a JSON object")
    manifest = PortableAgentBundleManifest.from_dict(data)
    manifest.validate()
    return manifest


def evaluate_bundle_compatibility(
    manifest: PortableAgentBundleManifest,
    *,
    cli_version: str = CLI_VERSION,
    supported_schema_version: int = BUNDLE_SCHEMA_VERSION,
    runner_kind: str = "local",
) -> AgentBundleCompatibilityReport:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest.validate()
    except ValueError as exc:
        return AgentBundleCompatibilityReport(compatible=False, errors=(str(exc),))

    current_version = _parse_semver(cli_version, "cli_version")
    minimum_version = _parse_semver(
        manifest.compatibility.min_cli_version,
        "compatibility.min_cli_version",
    )
    if current_version < minimum_version:
        errors.append(
            f"bundle requires Beep.AI.Code >= {manifest.compatibility.min_cli_version}, current version is {cli_version}"
        )
    if manifest.compatibility.max_cli_version:
        maximum_version = _parse_semver(
            manifest.compatibility.max_cli_version,
            "compatibility.max_cli_version",
        )
        if current_version > maximum_version:
            errors.append(
                f"bundle supports Beep.AI.Code <= {manifest.compatibility.max_cli_version}, current version is {cli_version}"
            )
    if manifest.schema_version != supported_schema_version:
        errors.append(
            f"bundle schema_version {manifest.schema_version} is not supported by this CLI (expected {supported_schema_version})"
        )
    if runner_kind not in manifest.runtime.supported_runner_kinds:
        errors.append(
            f"bundle does not declare runner support for {runner_kind!r}: {manifest.runtime.supported_runner_kinds}"
        )
    if not manifest.compatibility.server_contract_versions:
        warnings.append("bundle does not yet declare Beep.AI.Server contract versions")
    if not manifest.compatibility.sdk_contract_versions:
        warnings.append("bundle does not yet declare JavaScript SDK contract versions")
    return AgentBundleCompatibilityReport(
        compatible=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


__all__ = [
    "AgentBundleAsset",
    "AgentBundleCompatibility",
    "AgentBundleCompatibilityReport",
    "AgentBundleModelConfig",
    "AgentBundleProvenance",
    "AgentBundleRuntimeRequirements",
    "AgentBundleSignature",
    "AgentBundleToolPolicy",
    "BUNDLE_KIND",
    "BUNDLE_SCHEMA_VERSION",
    "PortableAgentBundleManifest",
    "evaluate_bundle_compatibility",
    "validate_bundle_payload",
]