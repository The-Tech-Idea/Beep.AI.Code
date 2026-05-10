# Phase 1 — Agent Tool Layer

**Goal:** Make the tool layer a world-class coding-agent surface.
Every tool must have precise descriptions, declare optional params correctly,
return structured, actionable output, and be individually testable.

---

## Todo Tracker

### Fixes

- [x] `base.py` — `to_openai_tool()` marked ALL params as required regardless of `optional_params`.
  Fixed: introduced `optional_params: list[str]` hook; required list excludes optional keys.

- [x] `file_read.py` — No line cap; LLM could request entire 10k-line file in one call.
  Fixed: capped at 300 lines per call; response header includes `total_lines` and `showing: N-M`;
  truncation notice when more lines remain.

- [x] `file_write.py` — `create_backup=True` left `.backup.<ts>` files in repo on every write.
  Fixed: `create_backup=False`; response reports bytes and line count.

- [x] `shell.py` — Exit code not surfaced in output; max timeout only 120 s (inadequate for builds);
  stderr silently dropped when stdout present.
  Fixed: `[exit_code: N]` header; max timeout raised to 300 s; stderr appended under `[stderr]` label;
  combined output capped at 10 000 chars with truncation notice.

- [x] `search.py` — All three params (`pattern`, `path`, `file_pattern`) were required in schema.
  Result cap was 100 with misleading "and N more" suffix; no case-insensitive option; no context lines.
  Fixed: `path`, `file_pattern`, `case_sensitive`, `context_lines` all optional; cap raised to 200
  with clearer message; `>` prefix on match line vs ` ` on context lines.

- [x] `file_edit.py` — `required` list still contains `file_path` AND `edit` — correct,
  but description does not warn about whitespace sensitivity. Both `FileEditTool` and `SingleEditTool`
  share no workspace-path guard helper (copy-paste). Extract shared `_WorkspaceGuard` mixin.

- [x] `file_edit.py` — `apply_blocks_from_text` returns `messages` but the tool truncates them;
  full feedback should reach the LLM so it can self-correct.

- [x] `approval.py` — `single_edit` not in `DESTRUCTIVE_TOOLS`; it writes files.
  Verified: `single_edit` is already guarded in `DESTRUCTIVE_TOOLS`; read-only `list_directory` remains unguarded.

### Enhancements

- [x] `list_directory.py` — New tool. Lists a directory flat or recursively, respects IgnoreMatcher,
  capped at 500 entries with truncation notice.

- [x] `glob_files.py` — New tool: `glob_files(pattern, path?)`. Finds files matching a glob pattern
  relative to workspace root (e.g. `**/*.py`, `src/**/*.ts`). Returns relative paths, one per line.
  LLMs need this to discover files without reading the whole tree.

- [x] `git_tool.py` — New tool: `git(subcommand)`. Wraps `git status`, `git diff [file]`,
  `git log --oneline [-n N]`, `git add`, `git commit -m`, `git stash`.
  Subcommand is a string; tool validates against an allowlist and rejects anything else.
  Uses `workspace/git.py` helpers where possible.

- [x] `context_tool.py` — New tool: `read_files(paths: list[str])`. Batch-reads multiple files in
  one tool call and returns them concatenated with `## path` headers. Reduces round-trips when the
  agent knows it needs several files (e.g. to understand a call chain).

- [x] `factory.py` — Add `list_directory`, `glob_files`, `git_tool`, `context_tool` to
  `get_default_tools()`. Add a `read_only=True` mode that omits `file_write`, `file_edit`, and `shell`
  for review/explain use cases.

- [x] `base.py` — Add `is_read_only: bool` property (default `False`) so factory can filter tools
  for read-only agent modes.
  Implemented as the repository-standard `read_only_safe` property consumed by the factory's read-only filtering.

---

## Acceptance Criteria

1. `to_openai_tool()` schema: required params are only non-optional ones.
2. `file_read` response always includes total_lines header; never returns more than 300 lines.
3. `shell` response always starts with `[exit_code: N]`; stderr is visible in output.
4. `search` supports `case_sensitive=false` and returns context lines when requested.
5. `list_directory` and `glob_files` exist and are in `get_default_tools()`.
6. `git_tool` exists, is allowlisted, and uses `workspace/git.py` helpers.
7. All tool execute methods have direct unit tests in `tests/test_agent_tool_*.py`.
8. `approval.py` correctly guards `single_edit`.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/agent/tools/base.py` | ✅ Done |
| `beep/agent/tools/file_read.py` | ✅ Done |
| `beep/agent/tools/file_write.py` | ✅ Done |
| `beep/agent/tools/shell.py` | ✅ Done |
| `beep/agent/tools/search.py` | ✅ Done |
| `beep/agent/tools/list_directory.py` | ✅ Done |
| `beep/agent/tools/file_edit.py` | ✅ Done |
| `beep/agent/tools/glob_files.py` | 🆕 New |
| `beep/agent/tools/git_tool.py` | 🆕 New |
| `beep/agent/tools/context_tool.py` | 🆕 New |
| `beep/agent/tools/factory.py` | ✅ Done |
| `beep/agent/approval.py` | ✅ Done |
| `tests/test_agent_tool_file_read.py` | 🆕 New |
| `tests/test_agent_tool_file_write.py` | 🆕 New |
| `tests/test_agent_tool_shell.py` | 🆕 New |
| `tests/test_agent_tool_search.py` | 🆕 New |
| `tests/test_agent_tool_list_directory.py` | 🆕 New |
| `tests/test_agent_tool_git.py` | 🆕 New |
| `tests/test_agent_tool_factory.py` | 🔧 Extend |
