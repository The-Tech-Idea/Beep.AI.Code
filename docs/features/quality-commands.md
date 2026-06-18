# Quality Commands (Test, Lint, Review)

**Status:** Partial  
**Package:** `beep/commands/`, `beep/linter/`, `beep/standards/`

## Purpose

Run tests and linters, AI-assisted review, and standards checks from the CLI.

## Code locations

| Module | Role |
|--------|------|
| `commands/test.py` | Test runner |
| `commands/lint.py` | Lint + fix |
| `commands/review.py` | AI review |
| `linter/runner.py` | Linter dispatch |
| `standards/review.py` | StandardsReviewer |

## User surfaces

- `beep test`, `beep lint`, `beep review`
- REPL git/review helpers where wired

## Current behavior

- Framework detection for tests; timeout and watch mode
- Empty-output guardrails on one-shot paths (Phase 6)
- Graceful interrupt handling

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| QC-1 | `beep test --json` machine-readable output | P1 | CLI test |
| QC-2 | Unified `beep check` (test+lint+analyze) | P2 | Meta command |
| QC-3 | Review templates per language | P2 | Config test |
| QC-4 | Auto-fix loop: lint → agent → test | P3 | Doc workflow |
| QC-5 | CI recipe doc in `docs/` with sample workflow | P1 | Doc + workflow file |
