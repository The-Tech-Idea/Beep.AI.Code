"""Patch application and diff utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import unidiff
from diff_match_patch import diff_match_patch


def apply_patch(content: str, patch_text: str) -> tuple[bool, str]:
    """Apply a unified diff patch to source content."""
    try:
        patched = _apply_unidiff(content, patch_text)
        if patched is not None:
            return True, patched
    except Exception:
        pass

    try:
        patched = _apply_dmp(content, patch_text)
        if patched is not None:
            return True, patched
    except Exception:
        pass

    return False, "Failed to apply patch"


def apply_patch_to_file(file_path: str, patch_text: str) -> tuple[bool, str]:
    """Apply a unified diff patch to a file on disk."""
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"

    original = path.read_text(encoding="utf-8")
    success, result = apply_patch(original, patch_text)
    if success:
        path.write_text(result, encoding="utf-8")
        return True, f"Applied patch to {file_path}"
    return False, result


def _apply_unidiff(content: str, patch_text: str) -> str | None:
    parsed = unidiff.PatchSet(patch_text)
    if not parsed:
        return None

    lines = content.splitlines(keepends=True)
    result: list[str] = []
    for patch in parsed:
        if patch.is_modified_file:
            for hunk in patch:
                result.extend(hunk.apply(lines))
            return "".join(result)
    return None


def _apply_dmp(content: str, patch_text: str) -> str | None:
    dmp = diff_match_patch()
    patches = dmp.patch_fromText(patch_text)
    if not patches:
        return None
    result, success = dmp.patch_apply(patches, content)
    return result if all(success) else None


def generate_unified_diff(
    original: str, modified: str, path_a: str = "a/file", path_b: str = "b/file"
) -> str:
    """Generate a unified diff string between two versions."""
    from pathlib import Path
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f1:
        f1.write(original)
        f1.flush()
        path1 = f1.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f2:
        f2.write(modified)
        f2.flush()
        path2 = f2.name

    try:
        result = subprocess.run(
            ["diff", "-u", path1, path2],
            capture_output=True,
            text=True,
        )
        return result.stdout or result.stderr
    except (FileNotFoundError, OSError):
        import difflib

        return "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                modified.splitlines(keepends=True),
                fromfile=path_a,
                tofile=path_b,
            )
        )
    finally:
        Path(path1).unlink(missing_ok=True)
        Path(path2).unlink(missing_ok=True)
