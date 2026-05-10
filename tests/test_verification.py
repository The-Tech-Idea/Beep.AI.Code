"""Tests for the verification module."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import tempfile

from beep.agent.verification.test_runner import TestResult, _detect_framework, run_workspace_tests
from beep.agent.verification.lint_runner import LintResult, _detect_linter, run_workspace_lint
from beep.agent.verification.verifier import VerificationResult, VerificationRunner


class TestTestRunner:
    def test_detect_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            Path(td, "pyproject.toml").touch()
            assert _detect_framework(Path(td)) == "pytest"

    def test_detect_jest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            Path(td, "package.json").touch()
            assert _detect_framework(Path(td)) == "jest"

    def test_no_framework(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assert _detect_framework(Path(td)) is None

    def test_result_passed(self) -> None:
        assert TestResult(passed=True, output="ok").passed is True
        assert TestResult(passed=False, output="fail").passed is False

    @pytest.mark.asyncio
    async def test_no_framework_returns_skip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = await run_workspace_tests(Path(td))
            assert result.passed is True
            assert "No test framework" in result.output


class TestLintRunner:
    def test_detect_ruff(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            Path(td, "pyproject.toml").touch()
            detected = _detect_linter(Path(td))
            assert detected is not None
            assert detected[0] == "ruff"

    def test_detect_eslint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            Path(td, ".eslintrc").touch()
            detected = _detect_linter(Path(td))
            assert detected is not None
            assert detected[0] == "eslint"

    def test_no_linter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            assert _detect_linter(Path(td)) is None

    @pytest.mark.asyncio
    async def test_no_linter_returns_skip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = await run_workspace_lint(Path(td))
            assert result.passed is True
            assert "No linter" in result.output


class TestVerifier:
    def test_verification_result_passed(self) -> None:
        result = VerificationResult(
            tests=TestResult(passed=True, output="ok"),
            lint=LintResult(passed=True, output="ok"),
        )
        assert result.passed is True

    def test_verification_result_failed_tests(self) -> None:
        result = VerificationResult(
            tests=TestResult(passed=False, output="fail"),
            lint=LintResult(passed=True, output="ok"),
        )
        assert result.passed is False

    def test_verification_result_failed_lint(self) -> None:
        result = VerificationResult(
            tests=TestResult(passed=True, output="ok"),
            lint=LintResult(passed=False, output="errors"),
        )
        assert result.passed is False

    def test_to_message(self) -> None:
        result = VerificationResult(
            tests=TestResult(passed=True, output="5 passed", framework="pytest"),
            lint=LintResult(passed=True, output="no issues", linter="ruff"),
        )
        msg = result.to_message()
        assert "PASS" in msg
        assert "5 passed" in msg
