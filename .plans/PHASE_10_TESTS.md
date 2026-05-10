# Phase 10 — Test Coverage Gaps

**Goal:** Every production module must have a corresponding test file with
meaningful coverage. Tests must run fast, be self-contained, and mock all
external I/O (network, filesystem where appropriate, subprocess).

---

## Coverage Gaps (as of 2026-05-02)

| Module | Test File | Status | Priority |
|--------|-----------|--------|----------|
| `agent/tools/file_read.py` | `test_agent_tool_file_read.py` | ✅ Done | P1 |
| `agent/tools/file_write.py` | `test_agent_tool_file_write.py` | ✅ Done | P1 |
| `agent/tools/file_edit.py` | `test_agent_tool_file_edit.py` | 🆕 Missing | P1 |
| `agent/tools/shell.py` | `test_agent_tool_shell.py` | ✅ Done | P1 |
| `agent/tools/search.py` | `test_agent_tool_search.py` | ✅ Done | P1 |
| `agent/tools/list_directory.py` | `test_agent_tool_list_dir.py` | ✅ Done | P1 |
| `agent/tools/factory.py` | `test_agent_tool_factory.py` | ✅ Good | — |
| `agent/loop.py` | `test_agent_run_agent.py` | ⚠️ Partial | P1 |
| `agent/loop.py` | `test_agent_session.py` | ⚠️ Partial | P1 |
| `api/client.py` | `test_api_client.py` | ✅ Good | — |
| `api/payloads.py` | `test_api_payloads.py` | ✅ Good | — |
| `api/client.py (extended)` | `test_api_extended.py` | ✅ Good | — |
| `workspace/search_replace.py` | None | 🆕 Missing | P2 |
| `workspace/ignore.py` | None | 🆕 Missing | P2 |
| `workspace/file_ops.py` | None | 🆕 Missing | P2 |
| `workspace/git.py` | None | 🆕 Missing | P2 |
| `context/window.py` | None | 🆕 Missing | P2 |
| `context/builder.py` | None | 🆕 Missing | P2 |
| `memory/loader.py` | None | 🆕 Missing | P2 |
| `sessions/history.py` | None | 🆕 Missing | P2 |
| `coding/prompt_context.py` | None | 🆕 Missing | P2 |
| `coding/metadata.py` | None | 🆕 Missing | P3 |
| `chat/commands/*.py` | `test_chat_*` | ⚠️ Partial | P2 |
| `cli.py` | None | 🆕 Missing | P3 |
| `config.py` | None | 🆕 Missing | P2 |
| `planner/editor.py` | None | 🆕 Missing | P3 |
| `plugins/runtime.py` | None | 🆕 Missing | P3 |

---

## Todo Tracker

### P1 — Tool Tests

- [ ] **`test_agent_tool_file_read.py`**
  - Read a real temp file; assert header present, 300-line cap, start/end params work.
  - Assert `optional_params` contains `start_line`, `end_line`.
  - Assert workspace escape is blocked.

- [ ] **`test_agent_tool_file_write.py`**
  - Write a temp file; read it back; assert content matches.
  - Assert response reports correct byte count and line count.
  - Assert workspace escape is blocked.
  - Assert no `.backup.*` files are created.

- [ ] **`test_agent_tool_shell.py`**
  - Run `echo hello`; assert `[exit_code: 0]` in output; assert content includes "hello".
  - Run a command that exits non-zero; assert `[exit_code: N]`.
  - Run a command that produces stderr; assert `[stderr]` section present.
  - Assert output is capped at 10 000 chars with truncation notice.
  - Assert `timeout` is optional in schema.

- [ ] **`test_agent_tool_search.py`**
  - Create temp workspace with two files; search for a term present in one.
  - Assert match is returned with `>` prefix.
  - Assert `case_sensitive=False` finds a match in different case.
  - Assert `context_lines=2` returns surrounding lines with ` ` prefix.
  - Assert results capped at 200 with notice.

- [ ] **`test_agent_tool_list_dir.py`**
  - List a temp directory flat; assert files and dirs listed with `/` suffix on dirs.
  - List recursively; assert nested files appear.
  - Assert ignored files (`.git/`) are excluded.
  - Assert workspace escape is blocked.

- [ ] **`test_agent_tool_factory.py` — extend existing**
  - Assert `list_directory` is in the tools returned by `build_agent_tools()`.
  - Assert `glob_files` is in the tools after Phase 1 completes.
  - Assert `get_default_tools(read_only=True)` omits destructive tools.

- [ ] **`test_agent_run_agent.py` / `test_agent_session.py` — extend**
  - Test max-steps exit path: assert `run_reason == "max_steps"`.
  - Test total-limit exit: assert conversation is consistent (all `tool_calls` have matching `tool` messages).
  - Test API error retry: mock 429 → retry → success.

### P2 — Core Infrastructure Tests

- [ ] **`test_workspace_search_replace.py`**
  - Parse valid `<<<<<<< SEARCH / ======= / >>>>>>> REPLACE` block.
  - `find_best_match` finds exact match with confidence 1.0.
  - `find_best_match` finds fuzzy match above threshold.
  - `find_best_match` returns `None` when nothing is above 0.7.

- [ ] **`test_workspace_ignore.py`**
  - `.git/` files are ignored by default.
  - Custom `.beepignore` pattern overrides default.
  - Paths outside workspace root return `is_ignored=True`.

- [ ] **`test_context_window.py`**
  - `truncate_messages` keeps system message always.
  - Does not separate a `tool_calls` message from its `tool` responses.
  - Returns empty conversation (system only) when all messages exceed budget.

- [ ] **`test_memory_loader.py`**
  - `load_project_memory` returns empty `ProjectMemory` when no `.beep.md` exists.
  - Returns loaded content when `.beep.md` exists.
  - Loads `.beep/habits.md` if present.

- [ ] **`test_sessions_history.py`**
  - `append_message` creates file if absent; appends if present.
  - `list_sessions` returns sorted list.
  - `replace_session` overwrites the file atomically.

- [ ] **`test_config.py`**
  - `load_config` reads from file; env overrides win.
  - `save_config` round-trips cleanly.
  - Default values are sane (`temperature=0.2`, `max_tokens=None`).

### P3 — Secondary Tests

- [ ] **`test_cli.py`** — `beep version`, `beep status` (mocked), `beep setup --help`.
- [ ] **`test_coding_prompt_context.py`** — `build_workspace_system_prompt` includes memory sections.
- [ ] **`test_planner_editor.py`** — `EditPlan` apply succeeds; rollback restores original.
- [ ] **`test_plugins_runtime.py`** — Discovery skips inaccessible directories.

---

## Conventions

- All tests use `tmp_path` (pytest fixture) for file system work.
- Network calls are mocked with `httpx_mock` or `unittest.mock.AsyncMock`.
- No test may write to `~/.beepai/` — patch `CONFIG_DIR` to `tmp_path` in conftest.
- Test files are named `test_<module_area>_<component>.py`.
