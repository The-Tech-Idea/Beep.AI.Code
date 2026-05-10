from __future__ import annotations

import json
from pathlib import Path
import tomllib

from typer.testing import CliRunner

from beep import __version__ as CLI_VERSION
from beep.agent.bundle_contract import PortableAgentBundleManifest
from beep.cli import app
from beep.publishing.server_deploy_support import build_server_deployment_plan


def _bundle_fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "agent_bundles" / name


def _package_fixture_path(channel: str, name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "agent_packages" / channel / name


def _materialize_bundle_fixture(tmp_path: Path, name: str = "code_reviewer_export.json") -> Path:
    source = _bundle_fixture_path(name)
    bundle_path = tmp_path / "code-reviewer.beep-agent.json"
    bundle_path.write_text(source.read_text(encoding="utf-8").replace("__CLI_VERSION__", CLI_VERSION), encoding="utf-8")
    return bundle_path


def _read_fixture_text(path: Path) -> str:
    content = path.read_text(encoding="utf-8").replace("__CLI_VERSION__", CLI_VERSION)
    return content.rstrip("\n") + "\n"


def test_agent_package_command_writes_expected_npm_and_python_artifacts(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path)
    output_root = tmp_path / "packages"
    runner = CliRunner()

    result = runner.invoke(app, ["agent", "package", str(bundle_path), "--output", str(output_root)])

    assert result.exit_code == 0
    assert (output_root / "npm" / "package.json").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("npm", "package.json")
    )
    assert (output_root / "npm" / "index.cjs").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("npm", "index.cjs")
    )
    assert (output_root / "npm" / "README.md").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("npm", "README.md")
    )
    assert (output_root / "npm" / "release-metadata.json").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("npm", "release-metadata.json")
    )
    assert (output_root / "python" / "pyproject.toml").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("python", "pyproject.toml")
    )
    assert (
        output_root / "python" / "src" / "beep_agent_code_reviewer" / "__init__.py"
    ).read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("python", "__init__.py")
    )
    assert (output_root / "python" / "README.md").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("python", "README.md")
    )
    assert (output_root / "python" / "release-metadata.json").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("python", "release-metadata.json")
    )
    assert (
        output_root / "github-release" / "release-metadata.json"
    ).read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("github-release", "release-metadata.json")
    )
    assert (output_root / "github-release" / "RELEASE_NOTES.md").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("github-release", "RELEASE_NOTES.md")
    )
    assert (output_root / "container" / "Dockerfile").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("container", "Dockerfile")
    )
    assert (output_root / "container" / "entrypoint.sh").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("container", "entrypoint.sh")
    )
    assert (output_root / "container" / "README.md").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("container", "README.md")
    )
    assert (output_root / "container" / "release-metadata.json").read_text(encoding="utf-8") == _read_fixture_text(
        _package_fixture_path("container", "release-metadata.json")
    )


def test_agent_package_command_dry_run_does_not_write_files(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path)
    output_root = tmp_path / "packages"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "agent",
            "package",
            str(bundle_path),
            "--channel",
            "npm",
            "--output",
            str(output_root),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Dry-run packaging plan" in (result.stdout or "")
    assert "package.json" in (result.stdout or "")
    assert not output_root.exists()


def test_agent_package_outputs_preserve_bundle_metadata_across_channels(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path)
    output_root = tmp_path / "packages"
    runner = CliRunner()

    result = runner.invoke(app, ["agent", "package", str(bundle_path), "--output", str(output_root)])

    assert result.exit_code == 0
    npm_manifest = json.loads((output_root / "npm" / "package.json").read_text(encoding="utf-8"))
    python_project = tomllib.loads((output_root / "python" / "pyproject.toml").read_text(encoding="utf-8"))
    release_metadata = json.loads((output_root / "github-release" / "release-metadata.json").read_text(encoding="utf-8"))
    npm_release_metadata = json.loads((output_root / "npm" / "release-metadata.json").read_text(encoding="utf-8"))
    python_release_metadata = json.loads((output_root / "python" / "release-metadata.json").read_text(encoding="utf-8"))
    container_release_metadata = json.loads((output_root / "container" / "release-metadata.json").read_text(encoding="utf-8"))
    container_dockerfile = (output_root / "container" / "Dockerfile").read_text(encoding="utf-8")
    manifest = PortableAgentBundleManifest.from_dict(json.loads(bundle_path.read_text(encoding="utf-8")))
    deploy_plan = build_server_deployment_plan(
        manifest,
        server_url="http://localhost:8000",
        bundle_reference="code-reviewer.beep-agent.json",
    )

    assert npm_manifest["version"] == python_project["project"]["version"] == "1.0.0"
    assert npm_manifest["description"] == python_project["project"]["description"] == "Review code changes."
    assert npm_manifest["beepAgentBundle"]["agentId"] == "code-reviewer"
    assert npm_manifest["beepAgentBundle"]["bundlePath"] == "bundle/code-reviewer.beep-agent.json"
    assert npm_manifest["beepAgentBundle"]["releaseMetadataPath"] == "release-metadata.json"
    assert python_project["project"]["name"] == "beep-agent-code-reviewer"
    assert release_metadata["channel_metadata"]["asset_files"] == [
        "release-metadata.json",
        "assets/code-reviewer.beep-agent.json",
        "assets/SHA256SUMS",
    ]
    assert "code-reviewer.beep-agent.json" in container_dockerfile
    assert npm_release_metadata["shared_release_metadata"] == python_release_metadata["shared_release_metadata"]
    assert npm_release_metadata["shared_release_metadata"] == release_metadata["shared_release_metadata"]
    assert npm_release_metadata["shared_release_metadata"] == container_release_metadata["shared_release_metadata"]
    assert npm_release_metadata["shared_release_metadata"] == deploy_plan.shared_release_metadata
    assert release_metadata["shared_release_metadata"]["tag_name"] == "beep-agent-code-reviewer-v1.0.0"


def test_agent_package_command_dry_run_lists_release_and_container_outputs(tmp_path: Path) -> None:
    bundle_path = _materialize_bundle_fixture(tmp_path)
    output_root = tmp_path / "packages"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "agent",
            "package",
            str(bundle_path),
            "--channel",
            "github-release",
            "--channel",
            "container",
            "--output",
            str(output_root),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "release-metadata.json" in (result.stdout or "")
    assert "Dockerfile" in (result.stdout or "")
    assert not output_root.exists()