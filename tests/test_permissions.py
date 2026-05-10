"""Tests for permissions system."""

from __future__ import annotations

import tempfile
from pathlib import Path

from beep.permissions.manager import (
    SandboxMode,
    PermissionManager,
    coerce_sandbox_mode,
    PermissionRule,
    RiskLevel,
    TrustLevel,
    TrustZone,
)


class TestTrustLevel:
    def test_values(self) -> None:
        assert TrustLevel.FULL.value == "full"
        assert TrustLevel.READ_ONLY.value == "read_only"
        assert TrustLevel.ASK.value == "ask"
        assert TrustLevel.DENIED.value == "denied"


class TestSandboxMode:
    def test_values(self) -> None:
        assert SandboxMode.READ_ONLY.value == "read-only"
        assert SandboxMode.WORKSPACE_WRITE.value == "workspace-write"
        assert SandboxMode.FULL_TRUST.value == "full-trust"

    def test_coerce_legacy_toggle_values(self) -> None:
        assert coerce_sandbox_mode(True) == SandboxMode.READ_ONLY
        assert coerce_sandbox_mode(False) == SandboxMode.WORKSPACE_WRITE
        assert coerce_sandbox_mode("full") == SandboxMode.FULL_TRUST


class TestRiskLevel:
    def test_values(self) -> None:
        assert RiskLevel.SAFE.value == "safe"
        assert RiskLevel.DESTRUCTIVE.value == "destructive"


class TestPermissionRule:
    def test_create_rule(self) -> None:
        rule = PermissionRule(
            tool_name="test",
            risk=RiskLevel.LOW,
            auto_approve=True,
            description="Test rule",
        )
        assert rule.tool_name == "test"
        assert rule.risk == RiskLevel.LOW
        assert rule.auto_approve is True


class TestTrustZone:
    def test_create_zone(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            zone = TrustZone(path=Path(td), level=TrustLevel.FULL)
            assert zone.level == TrustLevel.FULL
            assert zone.allowed_tools == []


class TestPermissionManager:
    def test_default_rules(self) -> None:
        mgr = PermissionManager()
        assert "file_read" in mgr._rules
        assert "file_write" in mgr._rules
        assert "shell" in mgr._rules

    def test_file_read_auto_approved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            allowed, reason = mgr.check_permission(
                "file_read", {"file_path": "test.py"}, Path(td)
            )
            assert allowed is True
            assert "Auto-approved" in reason

    def test_search_auto_approved(self) -> None:
        mgr = PermissionManager()
        allowed, reason = mgr.check_permission(
            "search", {"pattern": "foo"}, Path.cwd()
        )
        assert allowed is True

    def test_shell_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            allowed, reason = mgr.check_permission(
                "shell", {"command": "ls"}, Path(td)
            )
            assert allowed is False
            assert "approval" in reason.lower()

    def test_dangerous_command_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            allowed, reason = mgr.check_permission(
                "shell", {"command": "rm -rf /"}, Path(td)
            )
            assert allowed is False
            assert "Dangerous" in reason

    def test_dangerous_format_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            allowed, reason = mgr.check_permission(
                "shell", {"command": "format C:"}, Path(td)
            )
            assert allowed is False

    def test_shell_blocked_in_read_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            decision = mgr.evaluate_permission(
                "shell",
                {"command": "pytest"},
                Path(td),
                sandbox_mode=SandboxMode.READ_ONLY,
            )
            assert decision.allowed is False
            assert "blocks shell" in decision.reason.lower()

    def test_file_write_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mgr = PermissionManager()
            target = root / "new.py"
            allowed, reason = mgr.check_permission(
                "file_write", {"file_path": str(target)}, root
            )
            assert allowed is False
            assert "approval" in reason.lower()

    def test_file_write_blocked_in_read_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mgr = PermissionManager()
            decision = mgr.evaluate_permission(
                "file_write",
                {"file_path": str(root / "new.py")},
                root,
                sandbox_mode=SandboxMode.READ_ONLY,
            )
            assert decision.allowed is False
            assert "blocks file_write" in decision.reason.lower()

    def test_file_write_auto_approved_in_full_trust_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mgr = PermissionManager()
            decision = mgr.evaluate_permission(
                "file_write",
                {"file_path": str(root / "new.py")},
                root,
                sandbox_mode=SandboxMode.FULL_TRUST,
            )
            assert decision.allowed is True
            assert decision.requires_approval is False

    def test_git_write_blocked_in_read_only_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mgr = PermissionManager()
            decision = mgr.evaluate_permission(
                "git",
                {"subcommand": "commit -m test"},
                root,
                sandbox_mode=SandboxMode.READ_ONLY,
            )
            assert decision.allowed is False
            assert "git mutation" in decision.reason.lower()

    def test_git_write_requires_approval_in_workspace_write_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mgr = PermissionManager()
            decision = mgr.evaluate_permission(
                "git",
                {"subcommand": "commit -m test"},
                root,
                sandbox_mode=SandboxMode.WORKSPACE_WRITE,
            )
            assert decision.allowed is True
            assert decision.requires_approval is True

    def test_unknown_tool_denied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            allowed, reason = mgr.check_permission("unknown", {}, Path(td))
            assert allowed is False
            assert "Unknown" in reason

    def test_set_rule_auto_approve(self) -> None:
        mgr = PermissionManager()
        mgr.set_rule("file_write", auto_approve=True)
        assert mgr._rules["file_write"].auto_approve is True

    def test_trust_zone_matching(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sub = root / "trusted"
            sub.mkdir()
            mgr = PermissionManager()
            mgr.add_trust_zone(TrustZone(path=sub, level=TrustLevel.FULL))

            level = mgr.get_trust_level(sub / "file.py")
            assert level == TrustLevel.FULL

    def test_default_trust_is_ask(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            level = mgr.get_trust_level(Path(td) / "file.py")
            assert level == TrustLevel.ASK

    def test_denied_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mgr = PermissionManager()
            p = Path(td) / "secret"
            mgr.add_denied_path(p)
            assert p in mgr._denied_paths

    def test_prompt_section(self) -> None:
        mgr = PermissionManager()
        section = mgr.to_prompt_section()
        assert "Permissions & Safety" in section
        assert "system directories" in section

    def test_dangerous_commands_list(self) -> None:
        mgr = PermissionManager()
        assert "rm -rf" in mgr.DANGEROUS_COMMANDS
        assert "shutdown" in mgr.DANGEROUS_COMMANDS
