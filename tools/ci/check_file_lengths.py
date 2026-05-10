"""Enforce the repository Python file-length policy."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).with_name("file_length_baseline.json")


@dataclass(frozen=True)
class FileMeasurement:
    path: str
    lines: int


@dataclass(frozen=True)
class CheckResult:
    max_lines: int
    scanned_files: int
    new_oversized: list[FileMeasurement]
    grown_oversized: list[tuple[FileMeasurement, int]]
    stale_baseline: list[str]

    @property
    def ok(self) -> bool:
        return not (self.new_oversized or self.grown_oversized or self.stale_baseline)


def _load_config(config_path: Path) -> tuple[int, list[str], dict[str, int]]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Config file must contain a JSON object: {config_path}")

    max_lines = payload.get("max_lines")
    roots = payload.get("roots")
    allowed_oversized = payload.get("allowed_oversized")
    if not isinstance(max_lines, int) or max_lines <= 0:
        raise RuntimeError("Config file must define a positive integer max_lines value")
    if not isinstance(roots, list) or not all(isinstance(root, str) and root for root in roots):
        raise RuntimeError("Config file must define a non-empty roots list")
    if not isinstance(allowed_oversized, dict):
        raise RuntimeError("Config file must define an allowed_oversized object")

    normalized_allowed: dict[str, int] = {}
    for path, line_count in allowed_oversized.items():
        if not isinstance(path, str) or not path:
            raise RuntimeError("allowed_oversized keys must be non-empty strings")
        if not isinstance(line_count, int) or line_count <= max_lines:
            raise RuntimeError(
                "allowed_oversized values must be integers greater than max_lines so the baseline stays explicit"
            )
        normalized_allowed[path.replace("\\", "/")] = line_count
    return max_lines, roots, normalized_allowed


def _count_lines(path: Path) -> int:
    with open(path, encoding="utf-8") as file_handle:
        return sum(1 for _ in file_handle)


def _iter_python_files(repo_root: Path, roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        root_path = (repo_root / root).resolve()
        if not root_path.exists():
            continue
        files.extend(path for path in root_path.rglob("*.py") if path.is_file())
    return sorted(files)


def check_file_lengths(repo_root: Path, *, config_path: Path = DEFAULT_CONFIG_PATH) -> CheckResult:
    max_lines, roots, allowed_oversized = _load_config(config_path)
    files = _iter_python_files(repo_root, roots)
    measurements = {
        path.relative_to(repo_root).as_posix(): _count_lines(path)
        for path in files
    }

    new_oversized: list[FileMeasurement] = []
    grown_oversized: list[tuple[FileMeasurement, int]] = []
    for relative_path, line_count in measurements.items():
        if line_count <= max_lines:
            continue
        allowed_limit = allowed_oversized.get(relative_path)
        measurement = FileMeasurement(path=relative_path, lines=line_count)
        if allowed_limit is None:
            new_oversized.append(measurement)
            continue
        if line_count > allowed_limit:
            grown_oversized.append((measurement, allowed_limit))

    stale_baseline: list[str] = []
    for relative_path, allowed_limit in sorted(allowed_oversized.items()):
        current_lines = measurements.get(relative_path)
        if current_lines is None:
            stale_baseline.append(f"{relative_path} is missing but still listed with baseline {allowed_limit}")
            continue
        if current_lines <= max_lines:
            stale_baseline.append(
                f"{relative_path} is now {current_lines} lines and should be removed from the baseline"
            )

    return CheckResult(
        max_lines=max_lines,
        scanned_files=len(files),
        new_oversized=sorted(new_oversized, key=lambda item: item.path),
        grown_oversized=sorted(grown_oversized, key=lambda item: item[0].path),
        stale_baseline=stale_baseline,
    )


def _print_failures(result: CheckResult) -> None:
    print(
        f"Python file-length check failed: limit {result.max_lines} lines across {result.scanned_files} files.",
        file=sys.stderr,
    )
    if result.new_oversized:
        print("New oversized files:", file=sys.stderr)
        for item in result.new_oversized:
            print(f"  - {item.path}: {item.lines} lines", file=sys.stderr)
    if result.grown_oversized:
        print("Baseline regressions:", file=sys.stderr)
        for item, allowed_limit in result.grown_oversized:
            print(
                f"  - {item.path}: {item.lines} lines (baseline {allowed_limit})",
                file=sys.stderr,
            )
    if result.stale_baseline:
        print("Stale baseline entries:", file=sys.stderr)
        for message in result.stale_baseline:
            print(f"  - {message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--config-file", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    try:
        result = check_file_lengths(
            repo_root=args.repo_root.resolve(),
            config_path=args.config_file.resolve(),
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if result.ok:
        print(
            f"Python file-length check passed: limit {result.max_lines} lines across {result.scanned_files} files."
        )
        return 0

    _print_failures(result)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())