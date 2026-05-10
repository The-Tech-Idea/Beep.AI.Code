from __future__ import annotations

import json

import pytest

from beep.agent.bundle_contract import (
    AgentBundleAsset,
    AgentBundleCompatibility,
    AgentBundleModelConfig,
    AgentBundleProvenance,
    AgentBundleRuntimeRequirements,
    AgentBundleSignature,
    AgentBundleToolPolicy,
    BUNDLE_KIND,
    BUNDLE_SCHEMA_VERSION,
    PortableAgentBundleManifest,
    evaluate_bundle_compatibility,
    validate_bundle_payload,
)


def test_portable_agent_bundle_manifest_round_trips() -> None:
    manifest = PortableAgentBundleManifest(
        agent_id="code-reviewer",
        name="Code Reviewer",
        description="Review code changes with focused tooling.",
        system_prompt="Review diffs carefully before suggesting edits.",
        model=AgentBundleModelConfig(
            provider_key="openai",
            base_url="https://api.openai.com",
            model_id="gpt-5.4",
            provider_options={"reasoning": {"effort": "medium"}},
        ),
        tool_policy=AgentBundleToolPolicy(
            allowed_categories=["workspace", "git"],
            blocked_tools=["shell"],
            allow_mcp_tools=False,
        ),
        mcp_server_ids=["github"],
        data_source_ids=["repo-index"],
        tags=["review", "safe-default"],
        assets=[
            AgentBundleAsset(key="prompt", disposition="embedded", content="prompt text"),
            AgentBundleAsset(
                key="rules",
                kind="rules",
                disposition="referenced",
                path="assets/rules.md",
            ),
            AgentBundleAsset(
                key="summary",
                kind="generated",
                disposition="generated",
                generated_from="import-summary",
            ),
        ],
        compatibility=AgentBundleCompatibility(
            min_cli_version="0.1.0",
            server_contract_versions=["agent-definition/v1"],
            sdk_contract_versions=["javascript-agent-bundles/v1"],
        ),
        runtime=AgentBundleRuntimeRequirements(
            python=">=3.11",
            supported_runner_kinds=["local", "beep-server"],
            required_capabilities=["tool-calling"],
            optional_capabilities=["vision"],
        ),
        provenance=AgentBundleProvenance(
            created_at="2026-05-08T12:00:00+00:00",
            created_by="tests",
            source_repository="The-Tech-Idea/Beep.AI.Code",
            source_revision="abc123",
            publisher="The-Tech-Idea",
            channel_annotations={"release": "preview"},
            signature=AgentBundleSignature(
                status="placeholder",
                algorithm="sha256-ed25519",
                key_id="bundle-key-1",
                digest_sha256="abc123",
            ),
        ),
        metadata={"guard": "strict"},
    )

    rebuilt = PortableAgentBundleManifest.from_dict(manifest.to_dict())

    assert rebuilt.to_dict() == manifest.to_dict()
    assert json.loads(rebuilt.to_json())["kind"] == BUNDLE_KIND


def test_portable_agent_bundle_manifest_accepts_server_style_id_field() -> None:
    manifest = PortableAgentBundleManifest.from_dict(
        {
            "id": "server-shape",
            "name": "Server Shape",
            "model": {"provider_key": "beep", "model_id": "coding-assistant"},
        }
    )

    assert manifest.agent_id == "server-shape"
    assert manifest.model.provider_key == "beep"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (["not", "an", "object"], "JSON object"),
        (
            {
                "agent_id": "portable-agent",
                "name": "Portable Agent",
                "provenance": {"created_at": "not-a-date"},
            },
            "ISO-8601",
        ),
        (
            {
                "agent_id": "portable-agent",
                "name": "Portable Agent",
                "provenance": {"signature": {"status": "pending"}},
            },
            "signature.status",
        ),
    ],
)
def test_validate_bundle_payload_rejects_invalid_schema(payload: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_bundle_payload(payload)


@pytest.mark.parametrize(
    ("asset", "message"),
    [
        (AgentBundleAsset(key="missing-content", disposition="embedded"), "inline content"),
        (
            AgentBundleAsset(key="absolute-path", disposition="referenced", path="/tmp/file.txt"),
            "bundle root",
        ),
        (
            AgentBundleAsset(key="windows-path", disposition="referenced", path="assets\\rules.md"),
            "use '/'",
        ),
        (
            AgentBundleAsset(key="missing-generator", disposition="generated"),
            "generation source",
        ),
    ],
)
def test_portable_agent_bundle_manifest_rejects_invalid_assets(
    asset: AgentBundleAsset,
    message: str,
) -> None:
    manifest = PortableAgentBundleManifest(agent_id="invalid-assets", name="Invalid", assets=[asset])

    with pytest.raises(ValueError, match=message):
        manifest.validate()


def test_evaluate_bundle_compatibility_reports_schema_version_and_runner_mismatch() -> None:
    manifest = PortableAgentBundleManifest(
        agent_id="portable-agent",
        name="Portable Agent",
        schema_version=BUNDLE_SCHEMA_VERSION + 1,
        compatibility=AgentBundleCompatibility(min_cli_version="0.2.0"),
        runtime=AgentBundleRuntimeRequirements(supported_runner_kinds=["beep-server"]),
    )

    report = evaluate_bundle_compatibility(
        manifest,
        cli_version="0.1.0",
        runner_kind="local",
    )

    assert report.compatible is False
    assert any("requires Beep.AI.Code >= 0.2.0" in error for error in report.errors)
    assert any("schema_version" in error for error in report.errors)
    assert any("runner support" in error for error in report.errors)


def test_evaluate_bundle_compatibility_accepts_local_bundle_and_surfaces_cross_repo_warnings() -> None:
    manifest = PortableAgentBundleManifest(
        agent_id="portable-agent",
        name="Portable Agent",
        compatibility=AgentBundleCompatibility(min_cli_version="0.1.0"),
        runtime=AgentBundleRuntimeRequirements(supported_runner_kinds=["local"]),
    )

    report = evaluate_bundle_compatibility(manifest, cli_version="0.1.0")

    assert report.compatible is True
    assert any("Beep.AI.Server contract versions" in warning for warning in report.warnings)
    assert any("JavaScript SDK contract versions" in warning for warning in report.warnings)


def test_evaluate_bundle_compatibility_rejects_bundle_above_max_supported_cli_version() -> None:
    manifest = PortableAgentBundleManifest(
        agent_id="portable-agent",
        name="Portable Agent",
        compatibility=AgentBundleCompatibility(
            min_cli_version="0.1.0",
            max_cli_version="0.2.0",
        ),
    )

    report = evaluate_bundle_compatibility(manifest, cli_version="0.3.0")

    assert report.compatible is False
    assert any("<= 0.2.0" in error for error in report.errors)