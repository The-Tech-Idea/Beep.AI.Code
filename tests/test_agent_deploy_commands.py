from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from beep import __version__ as CLI_VERSION
from beep.api.client import BeepAPIClient
from beep.cli import app
from beep.config import BeepConfig
from beep.publishing.server_deploy_support import build_server_deployment_plan


def _bundle_fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "agent_bundles" / name


def _deploy_fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "agent_deploy" / name


def _read_fixture_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("__CLI_VERSION__", CLI_VERSION)


def _materialize_bundle_fixture(tmp_path: Path, *, hosted: bool = False) -> Path:
    payload = json.loads(
        _bundle_fixture_path("code_reviewer_export.json").read_text(encoding="utf-8").replace(
            "__CLI_VERSION__",
            CLI_VERSION,
        )
    )
    if hosted:
        payload["runtime"]["supported_runner_kinds"] = ["beep.ai.server"]
        payload["compatibility"]["server_contract_versions"] = ["beep.ai.server.agent-bundle.v1"]
    bundle_path = tmp_path / "code-reviewer.beep-agent.json"
    bundle_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle_path


def test_import_agent_bundle_posts_expected_payload(mock_config: BeepConfig) -> None:
    client = BeepAPIClient(mock_config)
    with patch.object(client, "_request", new=AsyncMock(return_value={"success": True})) as request_mock:
        result = __import__("asyncio").run(
            client.import_agent_bundle({"agent_id": "portable-agent"}, overwrite=True)
        )

    assert result == {"success": True}
    request_mock.assert_awaited_once_with(
        "POST",
        "/ai-middleware/api/agents/bundles/import",
        json={
            "bundle": {"agent_id": "portable-agent"},
            "overwrite": True,
        },
    )


def test_server_deployment_plan_matches_local_fixture(tmp_path: Path) -> None:
    from beep.agent.bundle_contract import PortableAgentBundleManifest

    bundle_path = _materialize_bundle_fixture(tmp_path)
    manifest = PortableAgentBundleManifest.from_dict(json.loads(bundle_path.read_text(encoding="utf-8")))
    plan = build_server_deployment_plan(
        manifest,
        server_url="http://localhost:8000",
        bundle_reference="code-reviewer.beep-agent.json",
    )

    expected = json.loads(_read_fixture_text(_deploy_fixture_path("server_plan_local.json")))
    assert plan.to_dict() == expected


def test_agent_deploy_command_dry_run_reports_server_plan(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path)
    runner = CliRunner()

    with patch(
        "beep.commands.agent_deploy.load_config",
        return_value=BeepConfig(server_url="http://localhost:8000"),
    ):
        result = runner.invoke(app, ["agent", "deploy", str(bundle_path), "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run deploy plan" in (result.stdout or "")
    assert "/ai-middleware/api/agents/bundles/import" in (result.stdout or "")
    assert "beep-agent-code-reviewer-v1.0.0" in (result.stdout or "")
    assert "local_pc" in (result.stdout or "")


def test_agent_deploy_command_requires_api_token_for_live_deploy(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path)
    runner = CliRunner()

    with patch(
        "beep.commands.agent_deploy.load_config",
        return_value=BeepConfig(server_url="http://localhost:8000"),
    ):
        result = runner.invoke(app, ["agent", "deploy", str(bundle_path)])

    assert result.exit_code == 1
    assert "api_token" in (result.stdout or "")


def test_agent_deploy_command_calls_server_bundle_import_and_surfaces_result(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path, hosted=True)
    runner = CliRunner()
    fake_client = SimpleNamespace(
        import_agent_bundle=AsyncMock(
            return_value={
                "success": True,
                "created": True,
                "warnings": ["server import complete"],
                "contract_version": "beep.ai.server.agent-bundle.v1",
                "agent": {"id": "code-reviewer", "execution_target": "enterprise_server"},
            }
        ),
        close=AsyncMock(),
    )

    with patch(
        "beep.commands.agent_deploy.load_config",
        return_value=BeepConfig(server_url="http://localhost:8000", api_token="token"),
    ):
        with patch("beep.commands.agent_deploy.BeepAPIClient", return_value=fake_client):
            result = runner.invoke(app, ["agent", "deploy", str(bundle_path), "--force"])

    assert result.exit_code == 0
    assert "Deployed bundle code-reviewer" in (result.stdout or "")
    assert "enterprise_server" in (result.stdout or "")
    assert "server import complete" in (result.stdout or "")
    fake_client.import_agent_bundle.assert_awaited_once()
    _, kwargs = fake_client.import_agent_bundle.await_args
    assert kwargs["overwrite"] is True
    assert kwargs["bundle"]["agent_id"] == "code-reviewer"
    fake_client.close.assert_awaited_once()