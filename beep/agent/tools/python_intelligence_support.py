"""Shared helpers for Jedi-backed Python code intelligence."""

from __future__ import annotations

import keyword
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_IGNORED_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)
_MAX_DOCSTRING_CHARS = 1600


def load_jedi_api() -> tuple[type[Any], type[Any]]:
    try:
        from jedi import Project, Script
    except ImportError as exc:
        raise RuntimeError(
            'Jedi is not installed in the agent environment. Run "beep agent setup" to install Python code intelligence support.'
        ) from exc
    return Project, Script


def count_python_files(root: Path) -> int:
    count = 0
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [
            name
            for name in dir_names
            if name not in _IGNORED_DIR_NAMES and not name.startswith(".")
        ]
        if Path(current_root).name in _IGNORED_DIR_NAMES:
            continue
        count += sum(1 for file_name in file_names if file_name.endswith(".py"))
    return count


def coerce_line(value: Any) -> int:
    try:
        line = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid line value: {value!r}") from exc
    if line < 1:
        raise ValueError("line must be >= 1")
    return line


def coerce_column(value: Any) -> int:
    if value is None:
        return 0
    try:
        column = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid column value: {value!r}") from exc
    if column < 1:
        raise ValueError("column must be >= 1")
    return column - 1


def coerce_new_name(value: Any) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        raise ValueError("new_name is required")
    if not candidate.isidentifier() or keyword.iskeyword(candidate):
        raise ValueError(f"Invalid Python identifier for new_name: {candidate!r}")
    return candidate


def trim_docstring(value: Any) -> str | None:
    docstring = str(value or "").strip()
    if not docstring:
        return None
    if len(docstring) <= _MAX_DOCSTRING_CHARS:
        return docstring
    return docstring[: _MAX_DOCSTRING_CHARS - 3].rstrip() + "..."


def relative_path(workspace_root: Path, path_value: object | None) -> str:
    if path_value is None:
        return "<builtin>"
    try:
        path = Path(str(path_value)).resolve()
    except OSError:
        return str(path_value)
    try:
        return path.relative_to(workspace_root).as_posix()
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class PythonSymbolRecord:
    name: str
    kind: str
    location: str
    description: str
    docstring: str | None = None


@dataclass(frozen=True)
class PythonRenameResult:
    new_name: str
    touched_files: tuple[str, ...]
    file_renames: tuple[tuple[str, str], ...] = ()


def serialize_symbol(name: object, workspace_root: Path) -> PythonSymbolRecord:
    symbol_name = str(
        getattr(name, "name", None)
        or getattr(name, "full_name", None)
        or getattr(name, "description", None)
        or "unknown"
    )
    kind = str(getattr(name, "type", None) or "symbol")
    description = str(getattr(name, "description", None) or symbol_name)
    path_text = relative_path(workspace_root, getattr(name, "module_path", None))
    line = getattr(name, "line", None)
    column = getattr(name, "column", None)
    if isinstance(line, int) and line >= 1:
        location = f"{path_text}:{line}"
        if isinstance(column, int) and column >= 0:
            location = f"{location}:{column + 1}"
    else:
        location = path_text
    docstring_method = getattr(name, "docstring", None)
    docstring = trim_docstring(docstring_method() if callable(docstring_method) else None)
    return PythonSymbolRecord(
        name=symbol_name,
        kind=kind,
        location=location,
        description=description,
        docstring=docstring,
    )


def format_symbol_records(header: str, records: list[PythonSymbolRecord]) -> str:
    sections = [header]
    for index, record in enumerate(records, start=1):
        sections.append(f"{index}. {record.name} [{record.kind}] - {record.location}")
        if record.description and record.description != record.name:
            sections.append(record.description)
        if record.docstring:
            sections.append("```text")
            sections.append(record.docstring.rstrip())
            sections.append("```")
    return "\n".join(sections)


def format_rename_result(header: str, result: PythonRenameResult) -> str:
    sections = [header, f"New name: {result.new_name}"]
    if result.touched_files:
        sections.append("Affected files:")
        for index, path in enumerate(result.touched_files, start=1):
            sections.append(f"{index}. {path}")
    if result.file_renames:
        sections.append("File renames:")
        for index, (old_path, new_path) in enumerate(result.file_renames, start=1):
            sections.append(f"{index}. {old_path} -> {new_path}")
    return "\n".join(sections)


def coerce_top_k(value: Any) -> int:
    if value is None:
        return 10
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid top_k value: {value!r}") from exc
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    return min(top_k, 50)