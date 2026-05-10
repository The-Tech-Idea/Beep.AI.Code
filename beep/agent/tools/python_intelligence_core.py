"""Core Jedi-backed Python code intelligence helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from beep.agent.tools.python_intelligence_support import PythonRenameResult
from beep.agent.tools.python_intelligence_support import PythonSymbolRecord
from beep.agent.tools.python_intelligence_support import coerce_column as _coerce_column
from beep.agent.tools.python_intelligence_support import coerce_line as _coerce_line
from beep.agent.tools.python_intelligence_support import coerce_new_name as _coerce_new_name
from beep.agent.tools.python_intelligence_support import coerce_top_k as _coerce_top_k
from beep.agent.tools.python_intelligence_support import count_python_files as _count_python_files
from beep.agent.tools.python_intelligence_support import format_rename_result as _format_rename_result
from beep.agent.tools.python_intelligence_support import format_symbol_records as _format_symbol_records
from beep.agent.tools.python_intelligence_support import load_jedi_api as _load_jedi_api
from beep.agent.tools.python_intelligence_support import relative_path as _relative_path
from beep.agent.tools.python_intelligence_support import serialize_symbol as _serialize_symbol


class PythonJediAdapter:
    """Lazy Python code-intelligence adapter backed by Jedi."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        api_loader: Callable[[], tuple[type[Any], type[Any]]] | None = None,
        python_file_counter: Callable[[Path], int] | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._api_loader = api_loader or _load_jedi_api
        self._python_file_counter = python_file_counter or _count_python_files
        self._project: object | None = None

    def availability_report(self) -> dict[str, Any]:
        report = {
            "available": False,
            "backend": "jedi",
            "workspace_root": str(self._workspace_root),
            "python_files": 0,
            "error": None,
        }
        python_files = self._python_file_counter(self._workspace_root)
        report["python_files"] = python_files
        if python_files <= 0:
            report["error"] = "No Python files detected in the current workspace."
            return report
        try:
            self._load_api()
        except RuntimeError as exc:
            report["error"] = str(exc)
            return report
        report["available"] = True
        return report

    def _load_api(self) -> tuple[type[Any], type[Any]]:
        return self._api_loader()

    def _get_project(self) -> object:
        if self._project is None:
            project_type, _ = self._load_api()
            self._project = project_type(path=str(self._workspace_root))
        return self._project

    def _resolve_file(self, raw_path: str) -> Path:
        candidate = Path(str(raw_path or "").strip())
        if not candidate:
            raise ValueError("file_path is required")
        resolved = candidate if candidate.is_absolute() else (self._workspace_root / candidate)
        resolved = resolved.resolve()
        if self._workspace_root not in resolved.parents and resolved != self._workspace_root:
            raise ValueError(f"Path outside workspace: {raw_path}")
        if not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {resolved}")
        if resolved.suffix.lower() != ".py":
            raise ValueError(f"Python code intelligence only supports .py files: {resolved}")
        return resolved

    def _build_script(self, file_path: Path) -> object:
        _, script_type = self._load_api()
        return script_type(path=str(file_path), project=self._get_project())

    def hover(self, *, file_path: str, line: Any, column: Any = None) -> PythonSymbolRecord:
        resolved = self._resolve_file(file_path)
        script = self._build_script(resolved)
        line_number = _coerce_line(line)
        column_number = _coerce_column(column)
        names = list(script.infer(line=line_number, column=column_number))
        if not names:
            names = list(
                script.goto(
                    line=line_number,
                    column=column_number,
                    follow_imports=True,
                    follow_builtin_imports=False,
                )
            )
        if not names:
            raise ValueError(
                f"No Python symbol found at {_relative_path(self._workspace_root, resolved)}:{line_number}:{column_number + 1}."
            )
        return _serialize_symbol(names[0], self._workspace_root)

    def definitions(self, *, file_path: str, line: Any, column: Any = None) -> list[PythonSymbolRecord]:
        resolved = self._resolve_file(file_path)
        script = self._build_script(resolved)
        line_number = _coerce_line(line)
        column_number = _coerce_column(column)
        definitions = list(
            script.goto(
                line=line_number,
                column=column_number,
                follow_imports=True,
                follow_builtin_imports=False,
            )
        )
        if not definitions:
            raise ValueError(
                f"No Python definition found at {_relative_path(self._workspace_root, resolved)}:{line_number}:{column_number + 1}."
            )
        return [_serialize_symbol(item, self._workspace_root) for item in definitions]

    def references(self, *, file_path: str, line: Any, column: Any = None) -> list[PythonSymbolRecord]:
        resolved = self._resolve_file(file_path)
        script = self._build_script(resolved)
        line_number = _coerce_line(line)
        column_number = _coerce_column(column)
        references = list(
            script.get_references(
                line=line_number,
                column=column_number,
                include_builtins=False,
            )
        )
        if not references:
            raise ValueError(
                f"No Python references found at {_relative_path(self._workspace_root, resolved)}:{line_number}:{column_number + 1}."
            )
        unique_records: list[PythonSymbolRecord] = []
        seen: set[tuple[str, str, str]] = set()
        for reference in references:
            record = _serialize_symbol(reference, self._workspace_root)
            key = (record.name, record.kind, record.location)
            if key in seen:
                continue
            seen.add(key)
            unique_records.append(record)
        return unique_records

    def rename(self, *, file_path: str, line: Any, column: Any = None, new_name: Any) -> PythonRenameResult:
        resolved = self._resolve_file(file_path)
        script = self._build_script(resolved)
        line_number = _coerce_line(line)
        column_number = _coerce_column(column)
        target_name = _coerce_new_name(new_name)

        references = list(
            script.get_references(
                line=line_number,
                column=column_number,
                include_builtins=False,
            )
        )
        touched_files = tuple(
            sorted(
                {
                    _relative_path(self._workspace_root, getattr(reference, "module_path", None))
                    for reference in references
                }
            )
        )

        rename = getattr(script, "rename", None)
        if not callable(rename):
            raise RuntimeError("The active Jedi script does not expose rename refactoring.")
        refactoring = rename(line=line_number, column=column_number, new_name=target_name)

        apply = getattr(refactoring, "apply", None)
        if not callable(apply):
            raise RuntimeError("The active Jedi refactoring does not expose apply().")
        apply()

        file_renames: list[tuple[str, str]] = []
        get_renames = getattr(refactoring, "get_renames", None)
        if callable(get_renames):
            for old_path, new_path in get_renames():
                file_renames.append(
                    (
                        _relative_path(self._workspace_root, old_path),
                        _relative_path(self._workspace_root, new_path),
                    )
                )

        if not touched_files:
            touched_files = (_relative_path(self._workspace_root, resolved),)
        return PythonRenameResult(
            new_name=target_name,
            touched_files=touched_files,
            file_renames=tuple(file_renames),
        )

    def workspace_symbols(self, *, query: str, top_k: Any = None) -> list[PythonSymbolRecord]:
        search_query = str(query or "").strip()
        if not search_query:
            raise ValueError("query is required")
        limit = _coerce_top_k(top_k)
        project = self._get_project()
        search = getattr(project, "search", None)
        if not callable(search):
            raise RuntimeError("The active Jedi project does not expose workspace symbol search.")
        names = list(search(search_query, all_scopes=True))
        if not names:
            raise ValueError(f"No Python workspace symbols found for query: {search_query!r}.")
        unique_records: list[PythonSymbolRecord] = []
        seen: set[tuple[str, str, str]] = set()
        for name in names:
            record = _serialize_symbol(name, self._workspace_root)
            key = (record.name, record.kind, record.location)
            if key in seen:
                continue
            seen.add(key)
            unique_records.append(record)
            if len(unique_records) >= limit:
                break
        if not unique_records:
            raise ValueError(f"No Python workspace symbols found for query: {search_query!r}.")
        return unique_records
