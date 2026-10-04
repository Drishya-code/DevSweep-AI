# DevSweep AI — Phase 2: Persistent Storage and Execution History

## Scope and completion

Phase 2 adds SQLite-backed project and cleanup history, versioned schema initialization, conservative restart recovery, and frontend views backed by saved records. Phase 1 workspace authorization remains the source of filesystem authority. External grants and one-use AI analysis authorization remain memory-only. No Phase 3 file-content backup or restore work was started.

## Initial working-tree inventory

- Repository: `C:\Users\Drishya\DevSweepAI`; branch `main`; HEAD `94a3efa` (`Publish DevSweep frontend phases and baseline`), tracking `origin/main`.
- Initial staged changes: none.
- Initial unstaged tracked files: `.env.example`, `README.md`, `backend/ai/routes.py`, `backend/cleanup/engine.py`, `backend/cleanup/routes.py`, `backend/config.py`, `backend/main.py`, `backend/scanner/routes.py`, `backend/tests/test_detector.py`, `frontend/src/pages/AIAgent.tsx`, `frontend/src/pages/CleanupPlans.test.tsx`, `frontend/src/pages/CleanupPlans.tsx`, `frontend/src/pages/Projects.tsx`, `frontend/src/pages/ScanWorkspace.test.tsx`, `frontend/src/pages/ScanWorkspace.tsx`, and `frontend/src/types/api.ts`.
- Initial untracked Phase 1 work: `DEVSWEEP_PHASE1_REPORT.md`, the three files under `backend/security/`, and `backend/tests/test_workspace_access.py`. All remain present. Phase 1 logic was preserved; `backend/tests/test_detector.py` received only an additive temporary-database test-isolation change for Phase 2.
- Relevant ignored/generated paths observed: `backend/.env` (not opened, changed, or displayed), `backend/.venv/`, Python caches, `frontend/node_modules/`, existing `frontend/dist/`, `demo-project/.env`, and `demo-project/coverage/`. The existing `backend/.pytest_cache/` directory could not be enumerated because Windows denied access. No ignored files were deleted.
- The effective configured DB path was `C:\Users\Drishya\DevSweepAI\backend\data\devsweep.db`; it did not exist at inspection time. It was not initialized or migrated during this task. Tests used disposable SQLite databases under pytest temporary directories.

## Phase 1 preservation and safety invariants

All initial Phase 1 tracked changes and all Phase 1 untracked files remain in the working tree. Persistence records history but never grants access. Project IDs are SHA-256 identifiers derived from canonical path plus the Phase 1 directory identity, so a replacement at the same path receives a different project ID. A move also remains a separate historical location.

The database does not store external grant IDs, one-use analysis IDs, API keys, environment variables, or authorization objects. Scan payloads explicitly discard grant and analysis identifiers. Persisted plans cannot authorize execution: execution still requires the existing in-memory plan and current `ProjectAuthorization`, whose grant and directory identity are revalidated by Phase 1. A restart loses that authority, and old plans are exposed through history as `review_only` with `can_execute: false`.

The cleanup engine keeps its existing scanner allowlist, candidate validation, protected-path checks, DANGEROUS blocking, CAUTION approval, path containment, and authorization guard. Recording callbacks run around the existing guarded delete call; they do not decide whether a deletion is allowed. If a database attempt write fails before the filesystem operation, the delete is not called. If recording fails after a delete, history remains uncertain rather than claiming success.

## Persistence architecture and schema

`backend/persistence/database.py` uses the existing SQLAlchemy 2.x and `aiosqlite` dependencies. It provides async request/operation sessions and declarative tables, while small per-item execution events use short synchronous SQLite transactions from the worker thread that runs the existing synchronous filesystem engine.

Schema version 1 is tracked in both `schema_migrations` and SQLite `PRAGMA user_version`. The initial schema includes:

- `projects`: identity-scoped project metadata and last-access timestamp.
- `scans`: authorized successful scan summaries, project reference, status, and timestamp.
- `cleanup_plans` and `cleanup_plan_items`: plan metadata, scan link, backend-generated item path/action/risk/reason/size, approval state, and item metadata.
- `cleanup_executions` and `execution_outcomes`: execution lifecycle/counts and per-item attempt/outcome/bytes/verification state.
- `verification_results`: result status, timestamp, checks, and an explicit metadata-only summary.
- `protected_file_metadata`: pre-cleanup protected-file existence metadata, marked metadata-only.
- Foreign-key constraints and indexes for project, plan, scan, execution, and verification lookups.

No file contents, backup blobs, restoration data, or recovery snapshots are saved. Verification metadata cannot establish file recoverability.

### Migration and backup behavior

At startup the backend inspects an existing database in read-only mode and checks its integrity, schema version, and any colliding application-table columns. A newer schema or ambiguous/incompatible collision fails startup closed without proceeding. Before upgrading an existing version-0 SQLite file, it makes a unique timestamped sibling backup using SQLite's backup API, opens the backup read-only, and verifies `PRAGMA integrity_check`. Existing backups are never overwritten. Schema creation and version recording run transactionally; no tables or columns are dropped.

The configured application database was absent, so no real database migration or backup was needed or performed. The temporary migration tests verified the backup path and incompatible-schema refusal behavior.

## Persistence lifecycle and restart behavior

- A successful authorized scan is recorded only after scanner work and a final authorization revalidation. Scan responses add `scan_id` and `project_id`; history does not store `access_grant_id`.
- Plan generation persists the plan and items only after the existing Nebius authorization and backend candidate validation flow succeeds. Optional `scan_id` is checked server-side and must belong to the same project.
- Cleanup execution commits an `in_progress` record before the engine starts. Each item attempt is committed immediately before the filesystem call; completion/failure and byte counts are recorded immediately after. The execution runs in a worker thread so filesystem work and synchronous event writes do not block the async request loop.
- Final execution status is stored as `completed`, `partial`, `failed`, or `unknown`, with processed/deleted/skipped/failed/unknown counts and safe error summaries. Verification results and each item's verification status are persisted separately.
- Startup converts leftover `in_progress` executions to `interrupted`, preserves completed item outcomes, converts an unfinished item attempt to `unknown`, records a restart explanation, and never retries deletion. All persisted plans are marked/read as review-only after restart.
- Historical project listing compares the current canonical folder identity where it can be checked. Missing, changed, and grant-required paths are presented as unavailable/review states. These checks do not authorize filesystem operations.
- Plan creation/execution is not automatically resumed. The user must rescan and obtain fresh authorization before creating a new executable plan. Phase 1's external grants and one-use analysis records remain ephemeral.

## API and frontend integration

Existing endpoints and request contracts remain compatible; fields were added only where required. Scan responses add `scan_id` and `project_id`; the two plan-generation frontend paths pass the corresponding scan ID. Execution responses add `execution_id`, lifecycle status, skipped count, and unknown count.

New read endpoints are:

- `GET /api/cleanup/history/projects`
- `GET /api/cleanup/history/scans`
- `GET /api/cleanup/history/plans?project_id=...`
- `GET /api/cleanup/history/executions`
- `GET /api/cleanup/history/executions/{execution_id}`
- `GET /api/cleanup/history/summary`

Projects now displays saved project records, last successful scan details where available, and current availability. The Dashboard shows actual persisted record counts with loading/error states. Cleanup History loads real execution and per-item outcomes, distinguishes partial/failed/interrupted/unknown states, and explains that verification metadata is not a backup. Cleanup Plans can show the latest saved plan after project selection, but hides approval/execution controls for that historical record. Existing session/project flows remain in place.

README documentation covers DB configuration, migration/backup behavior, new endpoints, and the non-recoverability of protected-file metadata.

## Files changed

### Phase 2 implementation changes

- `README.md`
- `backend/cleanup/engine.py`
- `backend/cleanup/routes.py`
- `backend/main.py`
- `backend/scanner/routes.py`
- `backend/tests/test_detector.py` (isolates test DB paths; preserves prior Phase 1 test setup)
- `backend/persistence/__init__.py` (new)
- `backend/persistence/database.py` (new)
- `backend/tests/test_persistence.py` (new)
- `backend/tests/test_persistence_api.py` (new)
- `frontend/src/pages/CleanupHistory.tsx`
- `frontend/src/pages/CleanupHistory.test.tsx` (new)
- `frontend/src/pages/CleanupPlans.tsx`
- `frontend/src/pages/CleanupPlans.test.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Dashboard.test.tsx`
- `frontend/src/pages/Projects.tsx`
- `frontend/src/pages/Projects.test.tsx`
- `frontend/src/pages/ScanWorkspace.tsx`
- `frontend/src/types/api.ts`

### Pre-existing Phase 1 files retained

`.env.example`, `backend/ai/routes.py`, `backend/config.py`, `frontend/src/pages/AIAgent.tsx`, `frontend/src/pages/ScanWorkspace.test.tsx`, `backend/security/__init__.py`, `backend/security/routes.py`, `backend/security/workspace_access.py`, `backend/tests/test_workspace_access.py`, and `DEVSWEEP_PHASE1_REPORT.md` remain from Phase 1. Several of these also appear in Git's modified/untracked lists because the Phase 1 work is still uncommitted.

No other files were intentionally created. The production build regenerated the already-existing ignored `frontend/dist/` output.

## Verification results

All automated tests used temporary databases and project fixtures. No cleanup was run against the repository, `demo-project`, or a user project. The new execution test deletes only a fixture under pytest's temporary directory and checks that the execution/outcome records existed before the delete call.

- Backend: `backend\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` — **95 passed**, one existing Pydantic class-config deprecation warning.
- Focused persistence/API tests were also run during implementation; the final full suite includes them.
- Frontend: `npm test -- --reporter=dot` from `frontend/` — **56 passed across 10 files**. React Router future-flag and test `act(...)` warnings remain in existing test output.
- Production build: `npm run build` from `frontend/` — **passed** (`tsc` and Vite; 1,591 modules transformed).
- `git diff --check` — passed; Git emitted only the existing Windows LF-to-CRLF normalization warnings.
- No browser/manual verification or real Nebius request was performed; neither is needed to validate the persistence changes.

## Limitations and Phase 3 boundary

- Access-grant creation/revocation still has no frontend UI. External folders require a fresh Phase 1 grant, which remains process-memory-only.
- SQLite history has no retention/rotation policy yet; records can grow over time.
- A conflicting or ambiguous legacy database intentionally blocks startup for manual inspection; no actual user database was available to validate a live migration.
- Backend history APIs rely on Phase 1 loopback-only operation; authentication and multi-user access remain out of scope.
- Protected-file existence metadata and verification results are not file-content backups. The Restore page's simulated behavior and all genuine content snapshot/restore functionality remain Phase 3 work and were not changed.
- No scheduled cleanup, automatic execution, restoration, authentication, or unrelated redesign was added.

## Final Git state

- Branch remains `main`, tracking `origin/main`; HEAD remains `94a3efa`.
- Staged changes: none. Phase 1 and Phase 2 source/report changes are uncommitted and unstaged.
- `backend/data/devsweep.db` remains absent; no actual database or credential file was modified.
- No commit, push, reset, stash, clean, or branch change occurred.
