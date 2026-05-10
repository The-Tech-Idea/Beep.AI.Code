"""Generate a SHA256 checksum manifest for built release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


DEFAULT_OUTPUT_NAME = "SHA256SUMS.txt"
ARTIFACT_PATTERNS = ("*.whl", "*.tar.gz")


def _iter_release_artifacts(artifacts_dir: Path, *, output_file: Path) -> list[Path]:
    artifacts: list[Path] = []
    output_resolved = output_file.resolve()
    for pattern in ARTIFACT_PATTERNS:
        artifacts.extend(
            path
            for path in artifacts_dir.glob(pattern)
            if path.is_file() and path.resolve() != output_resolved
        )
    return sorted(artifacts, key=lambda path: path.name)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_checksum_manifest(artifacts_dir: Path, *, output_file: Path | None = None) -> Path:
    resolved_dir = artifacts_dir.resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = (output_file or (resolved_dir / DEFAULT_OUTPUT_NAME)).resolve()
    artifacts = _iter_release_artifacts(resolved_dir, output_file=manifest_path)
    if not artifacts:
        raise RuntimeError(f"No release artifacts found in {resolved_dir}")

    lines = [f"{_sha256(path)}  {path.name}" for path in artifacts]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--output-file", type=Path)
    args = parser.parse_args()

    try:
        manifest_path = generate_checksum_manifest(
            artifacts_dir=args.artifacts_dir,
            output_file=args.output_file,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())