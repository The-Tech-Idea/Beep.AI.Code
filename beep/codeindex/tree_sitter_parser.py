"""Tree-sitter based code parser for multi-language symbol extraction."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node
from tree_sitter_language_pack import get_language, get_parser

from beep.codeindex.symbols import CodeSymbol, SymbolKind

_LANGUAGE_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".cs": "c_sharp",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".rake": "ruby",
    ".gemspec": "ruby",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".php": "php",
}


class TreeSitterParser:
    """Multi-language code parser using tree-sitter."""

    def parse_file(self, file_path: str, source: str | None = None) -> list[CodeSymbol]:
        lang = self._detect_language(file_path)
        if not lang:
            return []
        text = source or Path(file_path).read_text(encoding="utf-8")
        try:
            parser = get_parser(lang)
        except LookupError:
            return []
        tree = parser.parse(bytes(text, "utf-8"))
        return self._extract_symbols(tree.root_node, file_path, text, lang)

    def parse_directory(
        self, dir_path: str, extensions: list[str] | None = None
    ) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        root = Path(dir_path)
        skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox"}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(skip in path.parts for skip in skip_dirs):
                continue
            if extensions and path.suffix not in extensions:
                continue
            if path.suffix in _LANGUAGE_EXT_MAP:
                try:
                    symbols.extend(self.parse_file(str(path)))
                except Exception:
                    pass
        return symbols

    def _detect_language(self, file_path: str) -> str | None:
        ext = Path(file_path).suffix.lower()
        return _LANGUAGE_EXT_MAP.get(ext)

    def _extract_symbols(self, node, file_path: str, source: str, lang: str) -> list[CodeSymbol]:
        symbols: list[CodeSymbol] = []
        self._walk_node(node, file_path, source, symbols)
        return symbols

    def _walk_node(self, node, file_path: str, source: str, symbols: list[CodeSymbol]) -> None:
        kind = self._classify_node(node)
        if kind:
            name = self._extract_name(node)
            sig = ""
            if kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                sig = self._extract_signature(node, source)
            if name:
                symbols.append(
                    CodeSymbol(
                        name=name,
                        kind=kind,
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        signature=sig,
                    )
                )
        for child in node.children:
            self._walk_node(child, file_path, source, symbols)

    def _classify_node(self, node) -> SymbolKind | None:
        t = node.type
        if t in ("function_definition", "function_declaration", "function_item"):
            return SymbolKind.FUNCTION
        if t in ("method_definition", "method", "method_declaration"):
            return SymbolKind.METHOD
        if t in ("class_declaration", "class_definition", "class"):
            return SymbolKind.CLASS
        if t == "interface_declaration":
            return SymbolKind.INTERFACE
        if t in ("import_statement", "import_from_statement", "import_declaration"):
            return SymbolKind.IMPORT
        return None

    def _extract_name(self, node) -> str | None:
        for child in node.children:
            if "identifier" in child.type or "name" in child.type or child.type == "constant":
                return child.text.decode("utf-8", errors="replace")
        for child in node.children:
            for grandchild in child.children:
                if "identifier" in grandchild.type or "name" in grandchild.type:
                    return grandchild.text.decode("utf-8", errors="replace")
        return None

    def _extract_signature(self, node, source: str) -> str:
        start = node.start_point[0]
        lines = source.splitlines()
        if start < len(lines):
            line = lines[start].strip()
            if len(line) > 100:
                line = line[:100] + "..."
            return line
        return ""
