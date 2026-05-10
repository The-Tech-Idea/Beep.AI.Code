"""Build a synthetic older wheel for upgrade smoke tests."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


IGNORE_PATTERNS = (
    ".git",
    ".tmp",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".pytest_basetemp",
    ".pytest_tmp*",
    ".ruff_cache",
    ".vs",
    ".vscode",
    ".artifact-*",
    ".upgrade-*",
    "dist",
    "build",
    "__pycache__",
)


def _replace_single(pattern: str, replacement: str, text: str, *, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Unable to update {label}; expected exactly one match")
    return updated


def _patch_versions(repo_root: Path, fixture_version: str) -> None:
    pyproject_path = repo_root / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject_text = _replace_single(
        r'^version = "[^"]+"$',
        f'version = "{fixture_version}"',
        pyproject_text,
        label="pyproject version",
    )
    pyproject_path.write_text(pyproject_text, encoding="utf-8")

    package_init = repo_root / "beep" / "__init__.py"
    init_text = package_init.read_text(encoding="utf-8")
    init_text = _replace_single(
        r'^__version__ = "[^"]+"$',
        f'__version__ = "{fixture_version}"',
        init_text,
        label="package __version__",
    )
    package_init.write_text(init_text, encoding="utf-8")


def build_fixture(source_root: Path, output_dir: Path, fixture_version: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="beep-upgrade-fixture-") as temp_dir:
        temp_root = Path(temp_dir) / "repo"
        shutil.copytree(
            source_root,
            temp_root,
            ignore=shutil.ignore_patterns(*IGNORE_PATTERNS),
        )
        _patch_versions(temp_root, fixture_version)
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(output_dir)],
            cwd=temp_root,
            check=True,
        )

    candidates = sorted(output_dir.glob("beep_ai_code-*.whl"))
    if not candidates:
        raise RuntimeError("Synthetic upgrade fixture build produced no wheel")
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fixture-version", required=True)
    args = parser.parse_args()

    wheel_path = build_fixture(
        source_root=args.source_root.resolve(),
        output_dir=args.output_dir.resolve(),
        fixture_version=args.fixture_version.strip(),
    )
    print(wheel_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())