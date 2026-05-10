# Phase 8 — Workspace Utilities

**Goal:** The workspace layer (`workspace/`) is shared by tools, chat, and
the agent loop. It must be reliable, consistent, and expose the full set
of primitives needed for production-quality code editing.

---

## Todo Tracker

### Fixes

- [x] **workspace/search_replace.py — `find_best_match` with `confidence < 0.7` silently
  returns `None`.** `FileEditTool` interprets `None` as "match not found" and the edit
  silently fails with no diagnostics.
  Fixed: `find_best_match(...)` now returns the best candidate `MatchResult` instead of
  swallowing low-confidence matches, and `apply_search_replace(...)` owns the acceptance
  threshold so failures report confidence plus the best candidate text back to the caller.

- [x] **workspace/file_ops.py — `write_file` does not ensure parent directory exists.**
  Fixed: `write_file(...)` now creates missing parent directories before writing, and the
  Phase 8 regression suite covers nested-path creation.

- [x] **workspace/file_ops.py — `create_diff` uses `unified_diff` without `lineterm=""`.**
  Fixed: `create_diff(...)` passes `lineterm=""`, and the Phase 8 regression suite
  asserts the rendered diff no longer contains double-blank-line artifacts.

- [x] **workspace/git.py — `get_git_diff(file_path=None)` returns empty string on non-Git
  repositories instead of raising.** Callers cannot distinguish "no changes" from
  "not a git repo".
  Fixed: `get_git_diff(...)` and `get_git_diff_for_file(...)` now short-circuit to `None`
  outside Git workspaces, and the Phase 8 tests cover the non-repo case explicitly.

- [x] **workspace/detector.py — `find_workspace_root` walks to `/` before falling back.**
  On Windows, `.parents` includes the drive root. Walking to `C:\` is fine but the
  resolver should stop at the user home directory to avoid spurious hits.
  Fixed: the resolver now stops at `Path.home()` before falling back to the starting path.

### Enhancements

- [x] **workspace/file_ops.py — Add `read_lines(path, start, end)` function.**
  Fixed: `read_lines(...)` exists as the shared pagination primitive, `workspace.read_file(...)`
  now delegates slicing to it, and `FileReadTool` uses it for total-line and windowed reads.

- [x] **workspace/search_replace.py — Add multi-block atomic apply.**
  Fixed: `apply_blocks_from_text(...)` validates all blocks against in-memory working content
  and returns the original file content unchanged when any block fails.

- [x] **workspace/file_tree.py — `build_tree` should respect `IgnoreMatcher`.**
  Fixed: `build_tree(...)` now accepts an optional matcher and filters ignored entries when
  provided; the Phase 8 regression suite covers both ignored and matcher-free paths.

- [x] **workspace/git.py — Add `get_recent_commits(n=5)` function.**
  Fixed: `get_recent_commits(...)` returns structured `CommitInfo` records and safely
  returns an empty list when Git metadata is unavailable.

- [x] **workspace/ — Add `binary_detector.py`.**
  Fixed: `is_binary_file(path)` probes the first 8 KB for null bytes, and both `file_read`
  and `context/builder.py` use it to reject or skip binary inputs.

---

## Acceptance Criteria

1. `write_file` creates missing parent directories.
2. `create_diff` output has no double newlines.
3. `find_best_match` returns a `MatchResult` with confidence score.
4. `git_diff` returns `None` (not `""`) for non-Git workspaces.
5. `is_binary_file` exists and is used by `file_read` and `context/builder.py`.
6. `build_tree` respects `IgnoreMatcher`.

---

## File Ownership

| File | Status |
|------|--------|
| `beep/workspace/file_ops.py` | ✅ Parent mkdir + read_lines + diff fix |
| `beep/workspace/search_replace.py` | ✅ MatchResult + atomic multi-block |
| `beep/workspace/git.py` | ✅ None for non-Git + get_recent_commits |
| `beep/workspace/detector.py` | ✅ Stop at home dir |
| `beep/workspace/file_tree.py` | ✅ IgnoreMatcher support |
| `beep/workspace/binary_detector.py` | ✅ New |
| `beep/agent/tools/file_read.py` | ✅ Use binary_detector + read_lines |
| `beep/context/builder.py` | ✅ Use binary_detector |
