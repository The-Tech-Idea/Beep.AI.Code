"""Models for code index symbols."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SymbolKind(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    MODULE = "module"


@dataclass
class CodeSymbol:
    """A symbol extracted from source code."""

    name: str
    kind: SymbolKind
    file_path: str
    start_line: int
    end_line: int = 0
    signature: str = ""
    docstring: str = ""

    def summary(self) -> str:
        loc = f"{self.file_path}:{self.start_line}"
        if self.end_line and self.end_line != self.start_line:
            loc += f"-{self.end_line}"
        sig = f" {self.signature}" if self.signature else ""
        return f"{self.kind.value} {self.name}{sig} ({loc})"
