from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tools" / "ci" / "check_file_lengths.py"


def _run_guard(repo_root: Path, config: dict[str, object]) -> subprocess.CompletedProcess[str]:
    config_path = repo_root / "file-length-config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(_script_path()),
            "--repo-root",
            str(repo_root),
            "--config-file",
            str(config_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_file_length_guard_passes_when_files_fit_limit() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo_root = Path(td)
        src_dir = repo_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "ok.py").write_text("print('ok')\n", encoding="utf-8")

        result = _run_guard(
            repo_root,
            {
                "max_lines": 3,
                "roots": ["src"],
                "allowed_oversized": {},
            },
        )

        assert result.returncode == 0
        assert "passed" in result.stdout.lower()


def test_file_length_guard_fails_for_new_oversized_file() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo_root = Path(td)
        src_dir = repo_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "too_long.py").write_text("a\nb\nc\nd\n", encoding="utf-8")

        result = _run_guard(
            repo_root,
            {
                "max_lines": 3,
                "roots": ["src"],
                "allowed_oversized": {},
            },
        )

        assert result.returncode == 1
        assert "new oversized files" in result.stderr.lower()
        assert "src/too_long.py: 4 lines" in result.stderr


def test_file_length_guard_fails_when_allowlisted_file_grows() -> None:
    with tempfile.TemporaryDirectory() as td:
        repo_root = Path(td)
        src_dir = repo_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "legacy.py").write_text("a\nb\nc\nd\ne\n", encoding="utf-8")

        result = _run_guard(
            repo_root,
            {
                "max_lines": 3,
                "roots": ["src"],
                "allowed_oversized": {"src/legacy.py": 4},
            },
        )

        assert result.returncode == 1
        assert "baseline regressions" in result.stderr.lower()
        assert "src/legacy.py: 5 lines (baseline 4)" in result.stderr