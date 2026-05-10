# Beep.AI.Code Copilot Instructions

- Treat `.plans/README.md`, `.plans/PHASE_*.md`, and `MASTER-TODO-TRACKER.md` as the authoritative backlog for roadmap implementation.
- Before broad implementation, refactor, or "continue" requests, read the phase index, the relevant phase file, and the master tracker, then continue from the next incomplete todo unless the user explicitly changes priority.
- Prefer finishing the open items in phases already marked in progress before starting unrelated later planned phases unless blocked or redirected.
- When completing a slice of roadmap work, update both the relevant phase document and `MASTER-TODO-TRACKER.md` in the same change.
- Do not treat the phase documents as passive notes. If the user asks for ongoing implementation, the default behavior is to advance the planned phases and their open todo items.
- Do not mark a phase complete until its acceptance criteria and verification steps are satisfied.