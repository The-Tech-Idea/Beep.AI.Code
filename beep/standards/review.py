"""Standards reviewer for post-edit validation."""

from __future__ import annotations

import re
from pathlib import Path

from beep.standards.models import ArchitectureProfile, ReviewIssue

_FORBIDDEN_IMPORTS = {
    "domain": ["infrastructure", "presentation"],
    "application": ["presentation"],
}

_LAYER_PATTERNS = {
    "domain": r"/domain/",
    "application": r"/application/",
    "infrastructure": r"/infrastructure/",
    "presentation": r"/presentation/",
}


class StandardsReviewer:
    def review(
        self,
        changed_files: list[str],
        content_map: dict[str, str],
        profile: ArchitectureProfile | None = None,
    ) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        for file_path in changed_files:
            content = content_map.get(file_path, "")
            if not content:
                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                except Exception:
                    continue
            issues.extend(self._check_layer_imports(file_path, content))
            issues.extend(self._check_large_functions(file_path, content))
        return issues

    def _check_layer_imports(self, file_path: str, content: str) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        source_layer = self._detect_layer(file_path)
        if not source_layer:
            return issues

        forbidden = _FORBIDDEN_IMPORTS.get(source_layer, [])
        for forbidden_layer in forbidden:
            pattern = _LAYER_PATTERNS.get(forbidden_layer, "")
            if pattern and re.search(pattern, content):
                issues.append(
                    ReviewIssue(
                        severity="error",
                        file_path=file_path,
                        rule="layer_dependencies",
                        message=f"Layer '{source_layer}' must not depend on '{forbidden_layer}'.",
                    )
                )
        return issues

    def _check_large_functions(self, file_path: str, content: str) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"\s*(def |async def )", line) and not line.strip().endswith(":"):
                continue
            if re.match(r"\s*(def |async def )", line):
                func_name = line.strip().split("(")[0].replace("def ", "").replace("async def ", "")
                func_len = self._get_function_length(lines, i)
                if func_len > 50:
                    issues.append(
                        ReviewIssue(
                            severity="warning",
                            file_path=file_path,
                            line=i + 1,
                            rule="clean_code",
                            message=f"Function '{func_name}' is {func_len} lines long. Consider splitting it.",
                        )
                    )
        return issues

    def _get_function_length(self, lines: list[str], start: int) -> int:
        indent = len(lines[start]) - len(lines[start].lstrip())
        length = 0
        for line in lines[start + 1 :]:
            if line.strip() == "":
                length += 1
                continue
            curr_indent = len(line) - len(line.lstrip())
            if curr_indent <= indent and line.strip():
                break
            length += 1
        return length

    def _detect_layer(self, file_path: str) -> str | None:
        path_lower = file_path.lower()
        if "domain" in path_lower:
            return "domain"
        if "application" in path_lower:
            return "application"
        if "infrastructure" in path_lower:
            return "infrastructure"
        if "presentation" in path_lower or "api" in path_lower or "controller" in path_lower:
            return "presentation"
        return None
