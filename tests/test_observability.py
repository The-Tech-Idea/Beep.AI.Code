"""Tests for JSON logging helpers and diagnostics visibility."""

from __future__ import annotations

from unittest.mock import patch

from beep.utils.json_logging import is_json_logging_enabled


def test_json_logging_env_flag_enabled() -> None:
    with patch.dict("os.environ", {"BEEP_LOG_JSON": "1"}):
        assert is_json_logging_enabled() is True


def test_json_logging_env_flag_disabled() -> None:
    with patch.dict("os.environ", {"BEEP_LOG_JSON": "0"}):
        assert is_json_logging_enabled() is False
