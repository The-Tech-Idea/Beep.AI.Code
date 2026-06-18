"""Tests for external tool detector."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from beep.integrations.tool_detector import ToolStatus, detect, detect_all


class TestDetect:
    def test_tool_found(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/rg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "ripgrep 14.0.0\nSIMD"
                mock_run.return_value.stderr = ""
                status = detect("ripgrep")
                assert status.found is True
                assert status.tool_id == "ripgrep"
                assert "/usr/bin/rg" in status.path
                assert "ripgrep" in status.version

    def test_tool_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            status = detect("semgrep")
            assert status.found is False
            assert status.tool_id == "semgrep"
            assert status.path == ""

    def test_tool_install_hint_when_not_found(self) -> None:
        with patch("shutil.which", return_value=None):
            status = detect("gh")
            assert status.found is False
            assert status.install_hint != ""

    def test_version_extraction_fallback(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""
                mock_run.return_value.stderr = "git version 2.40.0\n"
                status = detect("git")
                assert status.found is True
                assert "2.40.0" in status.version

    def test_subprocess_error_is_caught(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/unknown"):
            with patch("subprocess.run", side_effect=OSError("bad")):
                status = detect("node")
                assert status.found is True
                assert status.version == ""


class TestDetectAll:
    def test_detect_all_returns_list(self) -> None:
        with patch("shutil.which", return_value=None):
            results = detect_all()
            assert isinstance(results, list)
            assert len(results) > 0
            for r in results:
                assert isinstance(r, ToolStatus)
                assert r.found is False


class TestToolStatus:
    def test_dataclass_defaults(self) -> None:
        s = ToolStatus(tool_id="rg", found=True)
        assert s.path == ""
        assert s.version == ""
        assert s.install_hint == ""
