#!/usr/bin/env python3
"""Lint check: ensure no direct service instantiation outside AppService.

Usage:
    python scripts/check_singletons.py

Returns 0 if clean, 1 if violations found.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Services that must only be instantiated inside AppService
SERVICE_CLASSES = {
    "CodeAnalysisService",
    "BookmarkManager",
    "TaskManager",
    "PermissionManager",
    "HookConfig",
    "WatcherService",
    "LanguageRegistry",
    "ProjectTemplateRegistry",
    "BeepAPIClient",
    "MCPClient",
    "SmartContextBuilder",
    "AutoContextBuilder",
    "ChatContext",
    "TreeSitterParser",
    "PythonJediAdapter",
    "SembleIndexAdapter",
    "PluginRegistry",
    "ProjectTemplateValidator",
    "RollbackManager",
    "StandardsReviewer",
}

# Files allowed to instantiate services
ALLOWED_FILES = {
    "beep/app_service.py",
    "beep/hooks/manager.py",  # Factory for HookConfig singleton
}


def _find_violations(file_path: Path) -> list[tuple[int, str]]:
    """Return list of (line_number, class_name) violations.

    Only flags zero-argument calls — creating a specific data instance
    (e.g. HookConfig(hooks=[...])) is allowed.
    """
    violations = []
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Only flag zero-argument calls (singleton access pattern)
            if len(node.args) == 0 and len(node.keywords) == 0:
                if isinstance(func, ast.Name) and func.id in SERVICE_CLASSES:
                    violations.append((node.lineno, func.id))
                elif isinstance(func, ast.Attribute) and func.attr in SERVICE_CLASSES:
                    violations.append((node.lineno, func.attr))
    return violations


def main() -> int:
    beep_dir = Path(__file__).parent.parent / "beep"
    all_violations: list[tuple[str, int, str]] = []

    for py_file in beep_dir.rglob("*.py"):
        # Compute relative path from repo root
        rel = py_file.relative_to(py_file.parent.parent.parent).as_posix()
        # Also check just the beep/ prefix path
        rel_beep = py_file.relative_to(beep_dir.parent).as_posix()
        if rel in ALLOWED_FILES or rel_beep in ALLOWED_FILES:
            continue
        for lineno, class_name in _find_violations(py_file):
            all_violations.append((rel_beep, lineno, class_name))

    if all_violations:
        print("Singleton violations found:")
        print("(Services must be accessed via get_app_service(), not instantiated directly)")
        print()
        for rel, lineno, class_name in all_violations:
            print(f"  {rel}:{lineno}  {class_name}()")
        print()
        print(f"Total: {len(all_violations)} violation(s)")
        return 1

    print("No singleton violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
