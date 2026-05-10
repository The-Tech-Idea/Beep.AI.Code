# Workspace Documentation Index

Date: 2026-03-29
Scope: Top-level guidance for all projects under `Beep.AI.Server`.

## Read First

1. `docs/ENGINEERING_IMPLEMENTATION_GUIDELINES.md`
2. `.github/copilot-instructions.md`
3. The relevant project-level README and docs for the project you are changing.

## Canonical Workspace Rules

- `docs/ENGINEERING_IMPLEMENTATION_GUIDELINES.md`
  - mandatory engineering, refactoring, structure, API contract, and auth-boundary rules
- `.github/copilot-instructions.md`
  - concise workspace guidance and project map for day-to-day implementation

## Project Map

- `Beep.AI.Server`
  - canonical server runtime, website/admin surface, `/v1/*`, and `ai_middleware/api/*`
- `Beep.AI.Researcher`
  - researcher application integrating with the canonical server APIs
- `Beep.AI.SDK`
  - multi-language SDKs targeting the canonical server APIs
- `Beep.AI.Clients`
  - desktop/mobile/client applications using the canonical server APIs
- `Beep.AI.Jarvis`
  - sibling application under the same workspace contract

## Integration Rule Summary

- Use the server root URL as the configured base URL.
- Use `/v1/*` for OpenAI-compatible behavior.
- Use `/ai-middleware/api/*` for platform-specific extension behavior.
- API Bearer tokens are reserved for external APIs only: `/v1/*` and `/ai-middleware/api/*`.
- Website/admin pages and routes use only website/session auth plus admin/permission authorization when needed.
- Website code must not convert session cookies into Bearer headers to call token-only APIs.
- Do not mix website/session auth with application-token auth.
- Overview pages are runtime-first: setup only before environment readiness, then one primary dashboard/table surface after readiness.
- RAG overview specifically must show only environment setup before readiness and only the RAG database surface after readiness.
