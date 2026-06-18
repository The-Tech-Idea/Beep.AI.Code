# Code Analysis & Indexing

**Status:** Partial  
**Package:** `beep/codeanalysis/`, `beep/codeindex/`, `beep/languages/`

## Purpose

Static analysis, architecture insights, tree-sitter parsing, and language registry for tools and `beep analyze`.

## Code locations

| Module | Role |
|--------|------|
| `codeanalysis/service.py` | `CodeAnalysisService` |
| `codeanalysis/semgrep_analyzer.py` | Semgrep integration |
| `codeanalysis/architecture_analyzer.py` | Architecture pass |
| `codeindex/tree_sitter_parser.py`, `symbols.py` | Parsing |
| `languages/registry.py` | Language plugins |
| `commands/analyze.py` | CLI |

## User surfaces

- `beep analyze`
- Agent intelligence tools
- `AppService.code_analysis`, `tree_sitter_parser`

## Current behavior

- Project statistics and analyzer hooks
- Language-specific adapters (Python, TS, Go, …)

## Enhancement backlog

| ID | Enhancement | Priority | Verification |
|----|-------------|----------|----------------|
| CAI-1 | `beep analyze --format json` for CI | P1 | CLI test |
| CAI-2 | Cache analysis results per workspace hash | P2 | Unit test |
| CAI-3 | Optional Semgrep rule packs from config | P2 | Config test |
| CAI-4 | Symbol index CLI (`beep symbols <file>`) | P2 | New command test |
| CAI-5 | Wire architecture report into `beep review` | P2 | Integration |
