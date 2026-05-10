"""Tests for workspace module."""

import tempfile
from pathlib import Path

from beep.workspace.detector import find_workspace_root, get_relative_path
from beep.workspace.ignore import IgnoreMatcher


def test_find_workspace_root_with_git():
    """Test finding workspace root with .git directory."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / ".git").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        result = find_workspace_root(tmp_path / "src")
        assert result == tmp_path


def test_find_workspace_root_fallback():
    """Test fallback to current directory when no .git."""
    with tempfile.TemporaryDirectory(dir=Path.home()) as tmp:
        tmp_path = Path(tmp)
        subdir = tmp_path / "sub"
        subdir.mkdir()
        result = find_workspace_root(subdir)
        assert result == subdir


def test_get_relative_path():
    """Test getting relative path."""
    root = Path("C:\\workspace")
    path = Path("C:\\workspace\\src\\main.py")
    result = get_relative_path(path, root)
    assert "src" in result
    assert "main.py" in result


def test_ignore_matcher_default_patterns():
    """Test default ignore patterns."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        matcher = IgnoreMatcher(tmp_path)
        assert matcher.is_ignored(tmp_path / "__pycache__" / "cache.pyc")
        assert matcher.is_ignored(tmp_path / "node_modules" / "pkg")
        assert not matcher.is_ignored(tmp_path / "src")


def test_ignore_matcher_beepignore():
    """Test .beepignore file parsing."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / ".beepignore").write_text("*.log\nbuild/\n")
        matcher = IgnoreMatcher(tmp_path)
        assert matcher.is_ignored(tmp_path / "debug.log")
        assert matcher.is_ignored(tmp_path / "build" / "output.txt")
        assert not matcher.is_ignored(tmp_path / "src")
