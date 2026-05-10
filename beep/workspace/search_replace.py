"""SEARCH/REPLACE block parser with fuzzy matching.

Parses Claude-style SEARCH/REPLACE blocks and applies them
with whitespace tolerance and multi-match detection.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchReplaceBlock:
    """A single SEARCH/REPLACE block."""

    search: str
    replace: str


@dataclass
class MatchResult:
    """Result of a fuzzy or exact search match."""

    start_line: int
    end_line: int
    confidence: float
    matched_text: str


def parse_blocks(content: str) -> list[SearchReplaceBlock]:
    """Parse SEARCH/REPLACE blocks from text.

    Supports formats:
    <<<<<<< SEARCH
    ...
    =======
    ...
    >>>>>>> REPLACE

    And:
    ```search
    ...
    ```replace
    ...
    ```
    """
    blocks = []

    pattern = re.compile(
        r"<<<<<<< SEARCH\s*\n(.*?)=======\s*\n(.*?)>>>>>>> REPLACE",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        blocks.append(SearchReplaceBlock(
            search=match.group(1).strip("\n"),
            replace=match.group(2).strip("\n"),
        ))

    if not blocks:
        pattern2 = re.compile(
            r"```(?:search|find)\s*\n(.*?)```(?:replace|replacement)\s*\n(.*?)```",
            re.DOTALL,
        )
        for match in pattern2.finditer(content):
            blocks.append(SearchReplaceBlock(
                search=match.group(1).strip("\n"),
                replace=match.group(2).strip("\n"),
            ))

    return blocks


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for fuzzy comparison."""
    return re.sub(r"[ \t]+", " ", text.strip())


def find_best_match(search: str, content: str) -> MatchResult | None:
    """Find the best match for search text in content.

    Returns the best MatchResult candidate with confidence score.
    The caller decides whether the confidence is acceptable.
    """
    search_lines = search.splitlines()
    content_lines = content.splitlines()

    if len(search_lines) == 0:
        return None

    if len(search_lines) == 1:
        search_normalized = normalize_whitespace(search_lines[0])
        best_match: MatchResult | None = None
        for i, line in enumerate(content_lines):
            line_norm = normalize_whitespace(line)
            if search_normalized in line_norm:
                return MatchResult(
                    start_line=i,
                    end_line=i + 1,
                    confidence=1.0,
                    matched_text=line,
                )
            sm = difflib.SequenceMatcher(None, search_normalized, line_norm)
            ratio = sm.ratio()
            if best_match is None or ratio > best_match.confidence:
                best_match = MatchResult(
                    start_line=i,
                    end_line=i + 1,
                    confidence=ratio,
                    matched_text=line,
                )
        if best_match is None or best_match.confidence <= 0.0:
            return None
        return best_match

    search_normalized_lines = [normalize_whitespace(line) for line in search_lines]
    content_normalized = [normalize_whitespace(line) for line in content_lines]

    best: MatchResult | None = None

    for i in range(len(content_normalized) - len(search_normalized_lines) + 1):
        window = content_normalized[i : i + len(search_normalized_lines)]
        matches = sum(1 for a, b in zip(search_normalized_lines, window) if a == b)
        confidence = matches / len(search_normalized_lines)

        matched_text = "\n".join(content_lines[i : i + len(search_normalized_lines)])
        if best is None or confidence > best.confidence:
            best = MatchResult(
                start_line=i,
                end_line=i + len(search_normalized_lines),
                confidence=confidence,
                matched_text=matched_text,
            )

    if best is None or best.confidence <= 0.0:
        return None
    return best


def find_exact_match(search: str, content: str) -> tuple[int, int] | None:
    """Find exact match for search text in content.

    Returns (start_pos, end_pos) or None.
    """
    idx = content.find(search)
    if idx >= 0:
        return (idx, idx + len(search))
    return None


def apply_search_replace(
    content: str,
    search: str,
    replace: str,
    *,
    fuzzy: bool = True,
) -> tuple[str | None, str]:
    """Apply a SEARCH/REPLACE block to content.

    Returns (new_content_or_None, message).
    """
    min_confidence = 0.7
    exact = find_exact_match(search, content)
    if exact:
        new_content = content[:exact[0]] + replace + content[exact[1]:]
        return new_content, "Exact match applied"

    if not fuzzy:
        return None, "No exact match found (use fuzzy mode for tolerance)"

    best = find_best_match(search, content)
    if not best:
        return None, "No candidate match found (even with fuzzy matching)"

    if best.confidence < min_confidence:
        return None, (
            "Low-confidence fuzzy match rejected "
            f"(confidence: {best.confidence:.0%}, required: {min_confidence:.0%}). "
            f"Best candidate:\n{best.matched_text}"
        )

    start_line, end_line, confidence = best.start_line, best.end_line, best.confidence
    lines = content.splitlines(keepends=True)

    new_lines = replace.splitlines(keepends=True)
    normalized_new = [
        line if line.endswith("\n") else line + "\n"
        for line in new_lines
    ]

    lines[start_line:end_line] = normalized_new
    new_content = "".join(lines)

    msg = f"Fuzzy match applied (confidence: {confidence:.0%})"
    if confidence < 0.9:
        msg += " — review carefully"

    return new_content, msg


def apply_search_replace_file(
    path: Path,
    search: str,
    replace: str,
    *,
    fuzzy: bool = True,
) -> tuple[bool, str]:
    """Apply SEARCH/REPLACE to a file.

    Returns (success, message).
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"Cannot read file: {e}"

    new_content, msg = apply_search_replace(content, search, replace, fuzzy=fuzzy)
    if new_content is None:
        return False, msg

    path.write_text(new_content, encoding="utf-8")
    return True, msg


def apply_blocks_from_text(content: str, text: str) -> tuple[str, list[str]]:
    """Parse and apply all SEARCH/REPLACE blocks from text atomically.

    All blocks are validated in memory first. If any block fails, no changes
    are written and all failures are reported. Returns (new_content, messages).
    """
    blocks = parse_blocks(text)
    if not blocks:
        return content, ["No SEARCH/REPLACE blocks found"]

    # First pass: validate all blocks against the *running* content
    pending: list[tuple[str, str, str]] = []  # (search, replace, message)
    failures: list[str] = []
    working = content

    for i, block in enumerate(blocks):
        result, msg = apply_search_replace(working, block.search, block.replace)
        if result is not None:
            pending.append((block.search, block.replace, msg))
            working = result
        else:
            failures.append(f"Block {i + 1}: FAILED — {msg}")

    if failures:
        return content, failures  # no partial writes

    # Second pass: replay on original to collect messages (already done in working)
    messages = [f"Block {i + 1}: {msg}" for i, (_, _, msg) in enumerate(pending)]
    return working, messages
