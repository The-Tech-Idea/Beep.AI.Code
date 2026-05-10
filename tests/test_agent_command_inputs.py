from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import typer
from typer.testing import CliRunner

from beep.cli import app
from beep.commands.agent import agent_cmd, agent_resume_cmd
from beep.commands.agent_inputs import (
    build_agent_initial_user_content,
    build_agent_response_format,
)
from beep.config import BeepConfig
from beep.permissions.manager import SandboxMode


def test_build_agent_response_format_wraps_schema_file(tmp_path: Path) -> None:
    schema_path = tmp_path / "result-schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            }
        ),
        encoding="utf-8",
    )

    response_format = build_agent_response_format(
        response_json=False,
        response_schema=schema_path,
    )

    assert response_format == {
        "type": "json_schema",
        "json_schema": {
            "name": "result_schema",
            "schema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        },
    }


def test_build_agent_initial_user_content_reads_text_and_image(tmp_path: Path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("focus on parser output", encoding="utf-8")
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nmock-image")

    content = build_agent_initial_user_content(
        input_files=[text_path],
        input_images=[image_path],
    )

    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert "Attached file: notes.txt" in content[0]["text"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content[2] == {"type": "text", "text": "Attached image: diagram.png"}


def test_build_agent_initial_user_content_rejects_binary_non_images(tmp_path: Path) -> None:
    binary_path = tmp_path / "data.bin"
    binary_path.write_bytes(b"\x00\x01\x02")

    with pytest.raises(ValueError, match="appears to be binary"):
        build_agent_initial_user_content(input_files=[binary_path], input_images=None)


def test_build_agent_response_format_rejects_conflicting_flags() -> None:
    with pytest.raises(ValueError, match="Choose either --response-json or --response-schema"):
        build_agent_response_format(
            response_json=True,
            response_schema=Path("schema.json"),
        )


def test_agent_cmd_forwards_cli_response_format_and_multimodal_inputs(tmp_path: Path) -> None:
    schema_path = tmp_path / "response.json"
    schema_path.write_text(
        json.dumps({"type": "object", "properties": {"plan": {"type": "string"}}}),
        encoding="utf-8",
    )
    text_path = tmp_path / "brief.txt"
    text_path.write_text("Keep the change minimal.", encoding="utf-8")
    image_path = tmp_path / "brief.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nmock-image")
    run_agent_mock = AsyncMock(return_value=SimpleNamespace())
    config = BeepConfig(api_token="token")
    mcp_config = SimpleNamespace(enabled=False, servers=[])

    def fake_run_agent_operation(*, model: str | None, operation):
        del model
        asyncio.run(operation(None, config))

    with patch("beep.commands.agent.find_workspace_root", return_value=tmp_path):
        with patch("beep.commands.agent.resolve_mcp_configuration", return_value=mcp_config):
            with patch("beep.commands.agent.run_agent", run_agent_mock):
                with patch("beep.commands.agent._run_agent_operation", side_effect=fake_run_agent_operation):
                    agent_cmd(
                        "inspect the screenshot",
                        response_json=False,
                        response_schema=schema_path,
                        input_file=[text_path],
                        input_image=[image_path],
                    )

    assert run_agent_mock.await_count == 1
    kwargs = run_agent_mock.await_args.kwargs
    assert kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "response",
            "schema": {"type": "object", "properties": {"plan": {"type": "string"}}},
        },
    }
    assert kwargs["initial_user_content"][0]["type"] == "text"
    assert "Attached file: brief.txt" in kwargs["initial_user_content"][0]["text"]
    assert kwargs["initial_user_content"][1]["type"] == "image_url"
    assert kwargs["initial_user_content"][2] == {"type": "text", "text": "Attached image: brief.png"}


def test_agent_resume_cmd_forwards_cli_response_format(tmp_path: Path) -> None:
    schema_path = tmp_path / "response-format.json"
    schema_path.write_text(json.dumps({"type": "json_object"}), encoding="utf-8")
    resume_agent_mock = AsyncMock(return_value=SimpleNamespace())
    config = BeepConfig(api_token="token")
    mcp_config = SimpleNamespace(enabled=False, servers=[])

    def fake_run_agent_operation(*, model: str | None, operation):
        del model
        asyncio.run(operation(None, config))

    with patch("beep.commands.agent.find_workspace_root", return_value=tmp_path):
        with patch("beep.commands.agent.resolve_mcp_configuration", return_value=mcp_config):
            with patch("beep.commands.agent.resume_agent", resume_agent_mock):
                with patch("beep.commands.agent._run_agent_operation", side_effect=fake_run_agent_operation):
                    agent_resume_cmd(
                        "thread-9",
                        response_json=False,
                        response_schema=schema_path,
                        input_file=None,
                        input_image=None,
                    )

    assert resume_agent_mock.await_count == 1
    assert resume_agent_mock.await_args.kwargs["response_format"] == {"type": "json_object"}


def test_agent_resume_cmd_rejects_initial_input_flags(tmp_path: Path) -> None:
    text_path = tmp_path / "brief.txt"
    text_path.write_text("Keep the change minimal.", encoding="utf-8")

    with pytest.raises(typer.Exit):
        agent_resume_cmd(
            "thread-9",
            input_file=[text_path],
            sandbox=SandboxMode.WORKSPACE_WRITE,
        )


def test_beep_agent_cli_routes_new_input_flags() -> None:
    runner = CliRunner()
    with patch("beep.cli.agent_cmd") as agent_cmd_mock:
        result = runner.invoke(
            app,
            [
                "agent",
                "review",
                "this",
                "diagram",
                "--response-json",
                "--input-file",
                "brief.txt",
                "--input-image",
                "brief.png",
            ],
        )

    assert result.exit_code == 0
    agent_cmd_mock.assert_called_once_with(
        "review this diagram",
        max_steps=20,
        auto_approve=False,
        sandbox=SandboxMode.WORKSPACE_WRITE,
        model=None,
        no_plugins=False,
        response_json=True,
        response_schema=None,
        input_file=[Path("brief.txt")],
        input_image=[Path("brief.png")],
    )