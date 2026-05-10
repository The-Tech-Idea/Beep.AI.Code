"""Module entry point for code editing utilities."""

from __future__ import annotations

from beep.editing.diff import count_changed_lines, generate_diff
from beep.editing.libcst_tools import add_import, rename_symbol
from beep.editing.patch import apply_patch
from beep.editing.transaction import EditTransaction, EditRecord

__all__ = [
    "EditRecord",
    "EditTransaction",
    "add_import",
    "apply_patch",
    "count_changed_lines",
    "generate_diff",
    "rename_symbol",
]
