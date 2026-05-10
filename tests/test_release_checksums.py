from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


def _script_path() -> Path:
    return Path(__file__).resolve().parents[1] / "tools" / "ci" / "generate_release_checksums.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_generate_release_checksums_writes_manifest() -> None:
    script_path = _script_path()
    with tempfile.TemporaryDirectory() as td:
        dist_dir = Path(td) / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        wheel_path = dist_dir / "beep_ai_code-0.1.0-py3-none-any.whl"
        sdist_path = dist_dir / "beep_ai_code-0.1.0.tar.gz"
        wheel_path.write_bytes(b"wheel-bytes")
        sdist_path.write_bytes(b"sdist-bytes")

        result = subprocess.run(
            [sys.executable, str(script_path), "--artifacts-dir", str(dist_dir)],
            capture_output=True,
            text=True,
            check=True,
        )

        manifest_path = dist_dir / "SHA256SUMS.txt"
        assert manifest_path.exists()
        assert result.stdout.strip().casefold() == str(manifest_path).casefold()
        assert manifest_path.read_text(encoding="utf-8").splitlines() == [
            f"{_sha256(wheel_path)}  {wheel_path.name}",
            f"{_sha256(sdist_path)}  {sdist_path.name}",
        ]


def test_generate_release_checksums_fails_without_artifacts() -> None:
    script_path = _script_path()
    with tempfile.TemporaryDirectory() as td:
        dist_dir = Path(td) / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [sys.executable, str(script_path), "--artifacts-dir", str(dist_dir)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 1
        assert "No release artifacts found" in result.stderr