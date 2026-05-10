"""Tests for patch-based editing and SEARCH/REPLACE."""

from __future__ import annotations

from beep.workspace.apply_patch import apply_patch, parse_patch
from beep.workspace.search_replace import (
    apply_blocks_from_text,
    apply_search_replace,
    find_best_match,
    find_exact_match,
    normalize_whitespace,
    parse_blocks,
)


class TestParseBlocks:
    def test_parse_git_style(self) -> None:
        text = """
<<<<<<< SEARCH
old code
=======
new code
>>>>>>> REPLACE
"""
        blocks = parse_blocks(text)
        assert len(blocks) == 1
        assert blocks[0].search == "old code"
        assert blocks[0].replace == "new code"

    def test_parse_markdown_style(self) -> None:
        text = """
```search
old code
```replace
new code
```
"""
        blocks = parse_blocks(text)
        assert len(blocks) == 1
        assert blocks[0].search == "old code"

    def test_parse_multiple_blocks(self) -> None:
        text = """
<<<<<<< SEARCH
func1()
=======
func1_v2()
>>>>>>> REPLACE

<<<<<<< SEARCH
func2()
=======
func2_v2()
>>>>>>> REPLACE
"""
        blocks = parse_blocks(text)
        assert len(blocks) == 2

    def test_parse_no_blocks(self) -> None:
        assert parse_blocks("just regular text") == []


class TestNormalizeWhitespace:
    def test_tabs_to_spaces(self) -> None:
        assert normalize_whitespace("hello\t\tworld") == "hello world"

    def test_multiple_spaces(self) -> None:
        assert normalize_whitespace("hello    world") == "hello world"

    def test_trim(self) -> None:
        assert normalize_whitespace("  hello  ") == "hello"


class TestFindExactMatch:
    def test_found(self) -> None:
        result = find_exact_match("bar", "foo bar baz")
        assert result is not None
        assert result == (4, 7)

    def test_not_found(self) -> None:
        assert find_exact_match("xyz", "foo bar baz") is None

    def test_multiline(self) -> None:
        content = "line1\nline2\nline3\n"
        result = find_exact_match("line2\n", content)
        assert result is not None


class TestFindBestMatch:
    def test_exact(self) -> None:
        result = find_best_match("hello world", "foo hello world bar")
        assert result is not None
        assert result.confidence == 1.0

    def test_fuzzy_whitespace(self) -> None:
        result = find_best_match("hello  world", "foo hello world bar")
        assert result is not None
        assert result.confidence > 0.7

    def test_low_confidence_candidate(self) -> None:
        result = find_best_match("xyz123", "foo bar baz")
        assert result is not None
        assert result.confidence < 0.7

    def test_partial_match(self) -> None:
        result = find_best_match("hello  world", "foo hello world bar")
        assert result is not None
        assert result.confidence >= 0.7


class TestApplySearchReplace:
    def test_exact_replace(self) -> None:
        content = "foo bar baz"
        result, msg = apply_search_replace(content, "bar", "qux")
        assert result == "foo qux baz"
        assert "Exact" in msg

    def test_fuzzy_replace(self) -> None:
        content = "foo\n  bar  \nbaz\n"
        result, msg = apply_search_replace(content, "bar", "qux")
        assert result is not None
        assert "qux" in result

    def test_no_match(self) -> None:
        result, msg = apply_search_replace("foo bar", "xyz", "qux", fuzzy=False)
        assert result is None

    def test_low_confidence_match_reports_best_candidate(self) -> None:
        result, msg = apply_search_replace("foo bar baz", "xyz123", "qux")
        assert result is None
        assert "Low-confidence fuzzy match rejected" in msg
        assert "Best candidate:" in msg

    def test_multiline_replace(self) -> None:
        content = "def old():\n    pass\n"
        search_text = "def old():\n    pass\n"
        replace_text = "def new():\n    return True\n"
        result, msg = apply_search_replace(content, search_text, replace_text)
        assert result is not None
        assert "def new():" in result


class TestApplyBlocksFromText:
    def test_single_block(self) -> None:
        content = "foo bar baz"
        edit = "<<<<<<< SEARCH\nbar\n=======\nqux\n>>>>>>> REPLACE"
        result, messages = apply_blocks_from_text(content, edit)
        assert result == "foo qux baz"

    def test_multiple_blocks(self) -> None:
        content = "foo bar baz qux"
        edit = (
            "<<<<<<< SEARCH\nfoo\n=======\nFOO\n>>>>>>> REPLACE\n\n"
            "<<<<<<< SEARCH\nqux\n=======\nQUX\n>>>>>>> REPLACE"
        )
        result, messages = apply_blocks_from_text(content, edit)
        assert result == "FOO bar baz QUX"

    def test_no_blocks(self) -> None:
        content = "foo bar"
        result, messages = apply_blocks_from_text(content, "no blocks here")
        assert result == content
        assert "No SEARCH/REPLACE" in messages[0]


class TestParsePatch:
    def test_simple_patch(self) -> None:
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 line1
-old
+new
 line3
"""
        patch = parse_patch(diff)
        assert patch.old_path == "test.py"
        assert patch.new_path == "test.py"
        assert len(patch.hunks) == 1

    def test_empty_diff(self) -> None:
        patch = parse_patch("")
        assert patch.hunks == []


class TestApplyPatch:
    def test_apply_simple_patch(self) -> None:
        content = "line1\nold\nline3\n"
        diff = (
            "--- a/test.py\n"
            "+++ b/test.py\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-old\n"
            "+new\n"
            " line3\n"
        )
        result = apply_patch(content, diff)
        assert result is not None
        assert "new" in result
        assert "old" not in result

    def test_apply_no_change(self) -> None:
        content = "line1\nold\nline3\n"
        diff = "--- a/test.py\n+++ b/test.py\n"
        result = apply_patch(content, diff)
        assert result is None
