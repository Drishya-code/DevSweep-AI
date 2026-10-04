# DevSweep AI — Master Roadmap

**Audit snapshot:** 2026-10-04. This document records the current implementation and the approved sequence for future work. It is a roadmap, not authorization to begin a phase.

## Product and safety principles

DevSweep helps developers understand and safely manage generated workspace artifacts. The workflow is: scanner gathers evidence, AI may explain/recommend, backend validates, user approves, cleanup engine executes, verification records outcomes, and a future recovery system restores verified backups.

The backend remains authoritative for workspace access, candidate identity, risk, approval, execution, and verification. `SAFE` items still require normal validation and approval; `CAUTION` requires explicit approval; `DANGEROUS` must remain blocked. AI output is untrusted and cannot authorize filesystem actions. Preserve local-only operation, exact-folder grants, path containment, protected paths, and secret handling. Never describe metadata as a content backup.

## Current phase status

“Complete” below means the scoped implementation and tests are reported complete; manual/live checks and limitations are called out separately. Reports are evidence, and this snapshot also checks the implementation.

| Phase | Status | Evidence | Remaining work |
|---|---|---|---|
| 0 — Baseline | Completed | `DEVSWEEP_PHASE0_BASELINE.md`; architecture/contracts and safety flow recorded. | Baseline test caveat is documented: one backend test outside the initial exclusion filter deleted only a temporary fixture. |
| 1 — Security and workspace boundary | Completed for scoped implementation | `DEVSWEEP_PHASE1_REPORT.md`; `backend/security/`, authorization checks in scanner/AI/cleanup routes, loopback defaults, focused security tests. | External-folder grant/revoke has no normal UI flow; grants are ephemeral. Phase 8 still needs an integrated security audit. |
| 2 — Persistence and execution history | Completed for implementation and reported tests | `DEVSWEEP_PHASE2_REPORT.md`; `backend/persistence/database.py`, persistence integration in cleanup/scanner routes, history APIs/UI and tests. | Configured live DB was absent, so migration against an existing user DB is unverified. No retention policy. Persistence is metadata/history only, not file-content recovery. |
| 3 — Real backup and restoration | Completed for scoped implementation and isolated tests | `DEVSWEEP_PHASE3_REPORT.md`; `backend/persistence/backups.py`, schema v2, backup-before-delete hook, restore APIs, and Restore Center. Full backend/frontend suites and production build pass. | No live DB migration or real-project restore was performed. Symlink-specific tests are skipped on this host. Backups are unencrypted and have no retention policy; directory restore may be partial and is reported. |
| 4 — Advanced AI workspace understanding | Partial | `backend/scanner/detector.py` has deterministic detection for Node, Python, C++, fixed artifact patterns, and size-based caution candidates. `backend/ai/routes.py` performs Nebius analysis and validates recommendations against scan candidates. | Broaden project detection and evidence/context, structured recommendation validation and provider resilience; ensure scanner and backend validation stay authoritative. |
| 5 — AI Agent | Partial | `/api/ai/chat` exists and can include a fresh project scan summary; `frontend/src/pages/AIAgent.tsx` provides the chat UI. | It has no controlled workspace tools, limited context rather than detailed scan/history evidence, and response-level provider/source disclosure and grounding need completion. No direct destructive tool should be added. |
| 6 — Frontend product experience | Partial | Existing C1–C3.2 work covers shared UI, adaptive views, themes, responsiveness, scan/plan/history flows, and error states. `frontend/src/App.tsx` includes the planned routes; Restore Center now uses verified backup APIs. | Some controls/claims and pages still need integration against real backend capabilities. Complete product-wide validation only after backend phases stabilize. |
| 7 — Settings and configuration | Partial | `frontend/src/pages/Settings.tsx` persists form values in browser `localStorage`; `/api/config` exposes limited read-only settings, while demo mode has app state. | Most displayed provider/workspace/scan settings do not update backend behavior. Define read-only vs mutable values, validated updates, safe secret policy, apply/restart semantics, and auditability before implementing. |
| 8 — Production readiness | Pending | No integrated release-readiness evidence found in the inspected reports/code. | Security/reliability/performance audit, restart and failure testing, documentation accuracy, fresh-install verification, release checks, and manual desktop/tablet/mobile checks. |

## Architecture and dependency alignment

- **Frontend:** React 18, TypeScript, Vite, React Router; `DevSweepContext` holds active workflow state, while view mode/theme preferences use frontend state/storage.
- **Backend:** FastAPI with scanner, AI, cleanup, and access routers. `backend/config.py` loads repository-root and backend `.env` files; backend `.env` takes precedence. Default backend host is loopback.
- **AI:** `backend/ai/factory.py` selects explicit demo/mock mode, configured Nebius, or an unconfigured mock provider. AI analysis authorization is short-lived and in-memory; mock analysis cannot authorize cleanup. Chat remains a separate conversational endpoint.
- **Filesystem safety:** `backend/security/workspace_access.py` canonicalizes and authorizes paths; scan, analysis, planning, execution, and verification revalidate access. Cleanup engine retains scanner candidate validation, protected-path checks, authoritative risk, dangerous blocking, caution approval, and execution checks.
- **Persistence:** SQLAlchemy/aiosqlite schema and versioned initialization are in `backend/persistence/database.py`. Cleanup plans/executions/outcomes/verification metadata and project/scan records are persisted. The configured live database was absent at the Phase 2 inspection; tests used temporary databases.
- **Recovery boundary:** persisted verification/protected-file metadata is not file content. Do not expose a file as recoverable until a Phase 3 backup was saved and hash-verified.

Dependency order remains **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**. Phase 3 now builds on Phase 2's durable execution identity/history. Phase 4 is the recommended next phase after review of the Phase 3 report; it depends on stable scanner and authorization boundaries. Phase 5 requires controlled tools and stable APIs; Phase 6 should integrate real capabilities rather than invent UI functionality; Phase 7 follows stable settings semantics; Phase 8 evaluates the integrated system.

### Compatibility and design gates

1. Before each endpoint change, compare its request/response schema, frontend callers, and tests. Prefer additive contract changes; coordinate backend and frontend changes.
2. Keep persisted records informational: they never grant workspace access or revive grants, AI analysis IDs, approvals, or plans after restart.
3. Phase 3 uses isolated per-user app-data by default, no automatic retention, SHA-256 manifests, fail-closed space checks, symlink/reparse refusal, and no-overwrite restore. Before adding encryption, retention/deletion, alternate shared storage, or overwrite conflict workflows, review the data-protection and recovery policy; original data must remain intact if backup write or verification fails.
4. Before Phase 7, decide which settings are runtime mutable, which are read-only, how updates are validated/applied/audited, and how secrets remain outside history/database and API responses.
5. Loopback-only binding is not authentication. Keep non-loopback access disabled until a separately reviewed authentication/deployment design exists.

## Recommended next phase: Phase 4 — Advanced AI workspace understanding

Phase 3 implementation is present and its isolated automated suites pass. Proceed with Phase 4 only after review of the Phase 3 report. Keep scope to:

- Broaden deterministic project detection while keeping the scanner and backend risk validation authoritative.
- Enrich workspace context with evidence from actual scanner findings and relevant safe project metadata; never infer removability from a filename alone.
- Harden structured recommendation validation for malformed, duplicate, missing, or hallucinated candidates and clearly surface provider timeouts/errors.
- Add isolated tests across supported project markers, generated artifacts, protected files, malformed AI output, and unknown project types.
- Keep AI recommendations advisory; do not weaken filesystem authorization, cleanup approval, verified backup, or restoration rules.

**Phase 4 definition of done:** project type and artifact context are evidence-based and testable; AI outputs map only to backend scanner candidates; unsupported or malformed recommendations cannot authorize an operation; all existing workspace and cleanup safety checks continue to hold.

## Git/worktree snapshot

Before this roadmap was added, branch `main` tracked `origin/main` with HEAD `94a3efa`; the working tree had 20 modified tracked files, 8 untracked entries, and no staged changes. The modifications include the uncommitted Phase 1/2 work and must be preserved. `backend/.env` is ignored and was not opened or changed. No database was present at the reported configured path. This audit did not run tests or cleanup operations, and did not stage, commit, push, reset, stash, or clean anything. This roadmap is the only file added by this task.

## Phase process

For each approved phase: inspect status and diffs; audit contracts, safety, and dependencies; list files/tests and any irreversible effects; stop for decisions when safety-critical behavior is ambiguous; implement only approved scope; test with temporary fixtures; inspect the final diff; write a `DEVSWEEP_PHASEN_REPORT.md` recording changes, test results, limitations, data/filesystem effects, and Git state. Never discard existing user changes, alter real credentials, or commit/push without explicit approval.
