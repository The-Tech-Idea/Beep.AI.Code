# Workspace Engineering Implementation Guidelines

Date: 2026-03-29
Purpose: Mandatory engineering standards for all implementation, refactor, integration, and planning work across every project under `Beep.AI.Server`.

Scope:
- `Beep.AI.Server`
- `Beep.AI.Researcher`
- `Beep.AI.SDK`
- `Beep.AI.Clients`
- `Beep.AI.Jarvis`
- shared solution-level scripts, docs, and tooling

## Non-Negotiable Standards

1. Production-ready code only.
   - Ship real runtime behavior, real validation, and real failure handling.
   - Do not leave placeholders, fake success responses, dead compatibility paths, or contract-only implementations in active delivery work.

2. Clean code is part of delivery.
   - Refactor while implementing.
   - If a change increases coupling, duplicates logic, or grows a god-file, split it before calling the task done.
   - Prefer divide-and-conquer module design: break large features into smaller focused files, services, adapters, and helpers instead of extending mixed files.

3. One primary responsibility per file.
   - Prefer one public class per file.
   - For function-based modules, keep one primary public responsibility per file.
   - Do not mix routes, orchestration, transport, persistence, formatting, and provider logic in the same file.

4. Keep files small and composable.
   - No code file may exceed `500` lines.
   - Treat roughly `300-450` lines as the warning zone.
   - If a file approaches the limit, split it before review becomes difficult.
   - If an existing file is already above `500` lines, do not grow it further; extract responsibilities until the touched surface is back under control.

5. Keep coordinators thin.
   - Routes/controllers/UI event handlers should parse input, call the correct service, and shape the response.
   - Orchestrators should delegate provider-specific or persistence-specific behavior to dedicated modules.

6. Use domain-owned folders.
   - Put code under the owning project and owning domain.
   - Do not dump new behavior into catch-all folders when a domain folder exists or should exist.

7. Prefer plug-and-play contracts when variability exists.
   - For providers, runtimes, frameworks, transport adapters, SDK targets, plugins, or client backends, define a clean contract first.
   - Extend through adapters, registries, factories, or provider modules instead of spreading conditional branching across the codebase.

8. Preserve compatibility intentionally.
   - Backward compatibility must be explicit.
   - Keep compatibility shims isolated and keep the canonical implementation clean.

9. Tests must follow the structure.
   - Add focused tests near the changed responsibility.
   - Prefer small direct tests for extracted modules plus route/service/integration tests for user-visible behavior.

10. Plans must include structure.
   - A plan is not complete if it only lists features and ignores file ownership, splits, and refactors.

## Workspace API Contract Rules

1. `Beep.AI.Server` is the canonical API host.
2. All local OpenAI-compatible APIs live under `/v1/*`.
3. All external extension APIs live under `/ai-middleware/api/*`.
4. API Bearer tokens are for external APIs only: all local OpenAI-compatible `/v1/*` APIs and all external extension `/ai-middleware/api/*` APIs.
5. Website/admin routes must use website/session auth only via `app.utils.permissions.require_auth` plus `permission_required(...)` or `admin_required(...)` when authorization is needed.
6. Website/admin route modules must not import `require_auth` from `app.middleware.token_auth`; that decorator is for application-token APIs only.
7. Website pages and their browser JavaScript must not convert website session cookies into Bearer `Authorization` headers in order to call `/v1/*` or `/ai-middleware/api/*`.
8. If a website page needs AJAX/JSON behavior, add a website/session-auth endpoint under the website route surface instead of calling a token-only API.
9. Application tokens are for external applications only.
10. Application tokens authenticate applications, not website users.
11. If an application request needs end-user context, pass it explicitly in the request contract.
12. SDKs and clients must use the server root URL as configuration input.
13. SDKs and clients must not require consumers to hardcode `/ai-middleware` into the base URL.
14. Standard OpenAI-compatible operations should go to `/v1/*`; platform-specific extensions should go to `/ai-middleware/api/*`.

## Structural Defaults

Use this shape unless there is a strong reason not to:

- `routes/` or transport-layer endpoints
  - thin HTTP/API surface only
- `services/<domain>/` or `services/`
  - coordinators, orchestration, policy, environment access, integration services
- `providers/` or provider-specific service modules
  - concrete backend/provider behavior
- `contracts/`
  - DTOs, interfaces, payload shapers, normalized contracts
- `runtime/`
  - runtime execution helpers and dispatch helpers
- `tests/`
  - focused tests per responsibility plus integration tests for visible behavior

## Website And Page Rules

1. Each page has one business function.
   - A page may support one user goal only.
   - If a page both configures runtime infrastructure and manages domain records, split it.

2. Overview pages are runtime-first.
   - Before the service environment exists, the overview page must show only environment creation and required package installation.
   - Do not show dashboards, record tables, analytics, flow diagrams, or secondary management controls before the environment is ready.

3. Ready-state overviews show one primary operational view only.
   - After the environment is ready, the overview page must switch to a single operational surface such as a dashboard summary or a CRUD-style table for the primary record type.
   - Do not use the overview page as a navigation hub that mixes multiple domains.

4. RAG canonical example.
   - Before setup: RAG overview shows only Create Environment and install required packages.
   - After setup: RAG overview shows only the primary RAG database management surface in a simple CRUD-style list or table.
   - Collections, storage, chunk templates, sync jobs, analytics, cache, and provider/package management remain on dedicated pages.

5. Template code must stay split.
   - JavaScript belongs in `static/js/<feature>/<page>.js`.
   - Page-specific CSS belongs in `static/css/<feature>/<page>.css` or the established feature stylesheet.
   - Do not leave inline `<script>`, inline `<style>`, or inline `onclick`/`onchange` handlers in website templates.

6. Website UX must be deliberate.
   - Primary CRUD pages should be list/table-first.
   - Major create/edit flows should use dedicated pages instead of modal-first CRUD.
   - Every touched page must have loading, empty, success, warning, and error states.
   - Pages must stay keyboard-accessible, mobile-usable, and visually clear.

7. RAG planning is document-driven.
   - For RAG website refactor work, consult `Beep.AI.Server/.plans/RAG_refactor/README.md` and the relevant phase document before implementation.
   - Do not introduce a new mixed RAG dashboard hub while implementing incremental changes.

## Project Expectations

### `Beep.AI.Server`
- Owns the runtime API contracts, website/admin surface, OpenAI compatibility surface, and `ai_middleware` extension surface.
- Must keep website/session auth clearly separated from application-token auth.
- Website pages must call website/session-auth routes only; do not wire website UI directly to token-only `/v1/*` or `/ai-middleware/api/*` endpoints unless the page is explicitly acting as an external API client by design.

### `Beep.AI.Researcher`
- Must integrate through the canonical server contract only.
- Use `/v1/*` for OpenAI-compatible flows and `/ai-middleware/api/*` for extension features like RAG, agents, extraction, and other platform-specific services.

### `Beep.AI.SDK`
- Every SDK target must normalize the server root URL correctly.
- Keep transport adapters thin and language-idiomatic.
- Keep OpenAI-compatible and middleware-specific surfaces clearly separated in the public API.

### `Beep.AI.Clients`
- Client apps must not bypass SDK or canonical server contracts without a deliberate reason.
- UI defaults, onboarding, and settings must reflect the real server contract.

### `Beep.AI.Jarvis`
- Must follow the same root server contract and the same auth separation rules.
- New server integrations should reuse shared SDK/client patterns where practical.

## Review Checklist

Before marking any task complete, confirm:

- the code is real and production-ready
- responsibilities are separated cleanly
- files remain small enough to review comfortably and no touched code file exceeds 500 lines
- the owning project and domain own the code
- compatibility shims are isolated
- SDK/client code targets the canonical server contract
- website/session auth and application-token auth remain clearly separated
- website pages do not turn session cookies into Bearer headers
- tests cover the changed responsibility directly
