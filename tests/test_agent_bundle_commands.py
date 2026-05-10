from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from beep import __version__ as CLI_VERSION
from beep.agent.bundle_contract import AgentBundleCompatibility, PortableAgentBundleManifest
from beep.agent.bundle_store import build_bundle_from_config
from beep.agent.loop import AgentRunResult
from beep.cli import app
from beep.config import BeepConfig


def _bundle_fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "agent_bundles" / name


def test_agent_export_command_writes_bundle_from_active_config(tmp_path: Path) -> None:
    output_path = tmp_path / "reviewer.beep-agent.json"
    runner = CliRunner()
    config = BeepConfig(
        agent_backend="openrouter",
        agent_base_url="https://openrouter.ai/api",
        agent_model="anthropic/claude-sonnet-4",
        agent_reasoning_effort="high",
        agent_parallel_tool_calls=False,
        project_id=17,
        mcp_enabled=True,
        mcp_servers=[{"name": "github", "command": "npx"}],
    )

    with patch("beep.commands.agent_bundle.load_config", return_value=config):
        result = runner.invoke(
            app,
            [
                "agent",
                "export",
                "code-reviewer",
                "--output",
                str(output_path),
                "--name",
                "Code Reviewer",
                "--description",
                "Review code changes.",
                "--tag",
                "review",
            ],
        )

    assert result.exit_code == 0
    manifest = PortableAgentBundleManifest.from_dict(json.loads(output_path.read_text(encoding="utf-8")))
    assert manifest.agent_id == "code-reviewer"
    assert manifest.name == "Code Reviewer"
    assert manifest.model.base_url == "https://openrouter.ai/api"
    assert manifest.model.provider_options == {
        "reasoning": {"effort": "high"},
        "parallel_tool_calls": False,
    }
    assert manifest.mcp_server_ids == ["github"]
    assert manifest.metadata == {"project_id": 17}


def test_agent_export_command_matches_canonical_fixture_when_timestamp_is_fixed(tmp_path: Path) -> None:
    output_path = tmp_path / "reviewer.beep-agent.json"
    fixture_path = _bundle_fixture_path("code_reviewer_export.json")
    runner = CliRunner()
    config = BeepConfig(
        agent_backend="openrouter",
        agent_base_url="https://openrouter.ai/api",
        agent_model="anthropic/claude-sonnet-4",
        agent_reasoning_effort="high",
        agent_parallel_tool_calls=False,
        project_id=17,
        mcp_enabled=True,
        mcp_servers=[{"name": "github", "command": "npx"}],
    )

    with patch("beep.commands.agent_bundle.load_config", return_value=config):
        with patch("beep.agent.bundle_store._utc_now_iso", return_value="2026-05-08T12:00:00+00:00"):
            result = runner.invoke(
                app,
                [
                    "agent",
                    "export",
                    "code-reviewer",
                    "--output",
                    str(output_path),
                    "--name",
                    "Code Reviewer",
                    "--description",
                    "Review code changes.",
                    "--tag",
                    "review",
                ],
            )

    assert result.exit_code == 0
    expected_payload = json.loads(fixture_path.read_text(encoding="utf-8").replace("__CLI_VERSION__", CLI_VERSION))
    expected_text = json.dumps(expected_payload, indent=2, sort_keys=True) + "\n"
    assert output_path.read_text(encoding="utf-8") == expected_text


def test_agent_import_command_installs_valid_bundle_into_library(tmp_path: Path) -> None:
    source_path = tmp_path / "portable.beep-agent.json"
    install_dir = tmp_path / "library"
    manifest = PortableAgentBundleManifest(
        agent_id="portable-agent",
        name="Portable Agent",
        compatibility=AgentBundleCompatibility(min_cli_version="0.1.0"),
    )
    source_path.write_text(manifest.to_json(), encoding="utf-8")

    runner = CliRunner()
    with patch("beep.agent.bundle_store.AGENT_BUNDLE_LIBRARY_DIR", install_dir):
        result = runner.invoke(app, ["agent", "import", str(source_path)])

    assert result.exit_code == 0
    installed_path = install_dir / "portable-agent.beep-agent.json"
    assert installed_path.exists()
    installed_manifest = PortableAgentBundleManifest.from_dict(
        json.loads(installed_path.read_text(encoding="utf-8"))
    )
    assert installed_manifest.to_dict() == PortableAgentBundleManifest.from_dict(
        json.loads(source_path.read_text(encoding="utf-8"))
    ).to_dict()


def test_agent_bundle_round_trip_export_then_import_preserves_supported_semantics(tmp_path: Path) -> None:
    export_path = tmp_path / "portable.beep-agent.json"
    install_dir = tmp_path / "library"
    runner = CliRunner()
    config = BeepConfig(
        agent_backend="anthropic",
        agent_base_url="https://api.anthropic.com",
        agent_model="claude-sonnet-4-20250514",
        agent_thinking_budget_tokens=2048,
        mcp_enabled=False,
    )

    with patch("beep.commands.agent_bundle.load_config", return_value=config):
        export_result = runner.invoke(
            app,
            [
                "agent",
                "export",
                "portable-agent",
                "--output",
                str(export_path),
                "--runner",
                "local",
            ],
        )

    assert export_result.exit_code == 0

    with patch("beep.agent.bundle_store.AGENT_BUNDLE_LIBRARY_DIR", install_dir):
        import_result = runner.invoke(app, ["agent", "import", str(export_path)])

    assert import_result.exit_code == 0
    exported_manifest = PortableAgentBundleManifest.from_dict(
        json.loads(export_path.read_text(encoding="utf-8"))
    )
    imported_manifest = PortableAgentBundleManifest.from_dict(
        json.loads((install_dir / "portable-agent.beep-agent.json").read_text(encoding="utf-8"))
    )
    assert imported_manifest.to_dict() == exported_manifest.to_dict()


def test_build_bundle_from_config_requires_configured_model() -> None:
    config = BeepConfig(agent_backend="openai", agent_model=None, default_model=None)

    try:
        build_bundle_from_config(config, agent_id="broken")
    except ValueError as exc:
        assert "agent_model or default_model" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected export builder to reject missing model configuration")


def test_agent_run_command_uses_imported_bundle_id_for_local_execution(tmp_path: Path) -> None:
    library_dir = tmp_path / "library"
    bundle_path = library_dir / "portable-agent.beep-agent.json"
    library_dir.mkdir()
    manifest = PortableAgentBundleManifest(
        agent_id="portable-agent",
        name="Portable Agent",
        model={"provider_key": "openai", "model_id": "gpt-5.4"},
        compatibility=AgentBundleCompatibility(min_cli_version="0.1.0"),
    )
    bundle_path.write_text(manifest.to_json(), encoding="utf-8")
    config = BeepConfig(
        agent_backend="openai",
        agent_api_key="token",
        agent_model="gpt-5.4",
    )
    resolved_mcp = type("ResolvedMcpConfiguration", (), {"servers": [], "enabled": False})()
    runner = CliRunner()

    with patch("beep.agent.bundle_store.AGENT_BUNDLE_LIBRARY_DIR", library_dir):
        with patch("beep.commands.agent_bundle.load_config", return_value=config):
            with patch("beep.commands.agent_bundle.find_workspace_root", return_value=tmp_path):
                with patch("beep.commands.agent_bundle.resolve_mcp_configuration", return_value=resolved_mcp):
                    with patch("beep.commands.agent_bundle.run_agent", new=AsyncMock(return_value=AgentRunResult(1, 0, "completed", "done"))) as run_agent_mock:
                        result = runner.invoke(app, ["agent", "run", "portable-agent", "inspect", "this", "repo"])

    assert result.exit_code == 0
    assert "Running bundle portable-agent" in (result.stdout or "")
    assert run_agent_mock.await_count == 1
    assert run_agent_mock.await_args.args[1] == "inspect this repo"
    kwargs = run_agent_mock.await_args.kwargs
    assert kwargs["config"].agent_backend == "openai"
    assert kwargs["config"].agent_model == "gpt-5.4"
    assert kwargs["bundle_manifest"].agent_id == "portable-agent"


def test_agent_run_command_requires_locally_available_bundle_mcp_servers(tmp_path: Path) -> None:
    library_dir = tmp_path / "library"
    bundle_path = library_dir / "portable-agent.beep-agent.json"
    library_dir.mkdir()
    manifest = PortableAgentBundleManifest.from_dict(
        {
            "agent_id": "portable-agent",
            "name": "Portable Agent",
            "model": {"provider_key": "openai", "model_id": "gpt-5.4"},
            "compatibility": {"min_cli_version": "0.1.0"},
            "tool_policy": {"allow_mcp_tools": True},
            "mcp_server_ids": ["github"],
        }
    )
    bundle_path.write_text(manifest.to_json(), encoding="utf-8")
    config = BeepConfig(
        agent_backend="openai",
        agent_api_key="token",
        agent_model="gpt-5.4",
    )
    resolved_mcp = type("ResolvedMcpConfiguration", (), {"servers": [], "enabled": False})()
    runner = CliRunner()

    with patch("beep.agent.bundle_store.AGENT_BUNDLE_LIBRARY_DIR", library_dir):
        with patch("beep.commands.agent_bundle.load_config", return_value=config):
            with patch("beep.commands.agent_bundle.find_workspace_root", return_value=tmp_path):
                with patch("beep.commands.agent_bundle.resolve_mcp_configuration", return_value=resolved_mcp):
                    result = runner.invoke(app, ["agent", "run", "portable-agent", "inspect", "this"])

    assert result.exit_code == 1
    assert "not available locally" in (result.stdout or "")