"""Tests for Coding Assistant response metadata parsing."""

from __future__ import annotations

from beep.coding.response_metadata import (
    count_pending_approvals,
    find_coding_identity,
    iter_json_objects,
)


def test_iter_json_objects_extracts_embedded_objects() -> None:
    objects = iter_json_objects('prefix {"a": 1} text {"b": {"c": 2}} suffix')
    assert objects == [{"a": 1}, {"b": {"c": 2}}]


def test_count_pending_approvals_handles_nested_metadata() -> None:
    text = """
Assistant text.
{"coding_assistant":{"pending_code_changes":[{"id":1},{"id":2}],"pending_approvals":[{"id":3}]}}
More text.
"""
    assert count_pending_approvals(text) == 3


def test_count_pending_approvals_ignores_invalid_json() -> None:
    assert count_pending_approvals('broken {"pending_code_changes":[{"id":1} text') == 0


def test_find_coding_identity_handles_nested_metadata() -> None:
    text = 'text {"coding_assistant":{"project_id":"42","session_id":"s-42"}}'
    assert find_coding_identity(text) == (42, "s-42")


def test_find_coding_identity_ignores_missing_metadata() -> None:
    assert find_coding_identity('{"status":"ok"}') == (None, None)
