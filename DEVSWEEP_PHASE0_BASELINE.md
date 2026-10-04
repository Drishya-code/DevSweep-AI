# DevSweep AI — Phase 0 Compatibility and Safety Baseline

**Purpose:** establish a read-only compatibility/safety baseline for the production-readiness work. This document records the implementation visible in the current working tree on 2026-10-02. It is not approval to begin Phase 1.

## Scope and preservation

The repository already contained extensive uncommitted work when Phase 0 began. No source code, schema, migration, environment file, or credential was edited. No cleanup was run against the application, demo-project, or user project; see the test caveat below regarding a test-owned temporary directory. No snapshot deletion or restoration was run. No commit or push was made. This document is the only file added for Phase 0.

Git reported **16 tracked modified files**, **22 existing untracked files**, and **no staged changes** before this document was added. The tracked diff was 1,927 insertions and 1,136 deletions. These are pre-existing changes and must remain intact:

### Tracked modified files

- backend/ai/routes.py
- backend/cleanup/routes.py
- backend/tests/test_detector.py
- frontend/src/App.tsx
- frontend/src/components/Sidebar.tsx
- frontend/src/components/TopBar.tsx
- frontend/src/index.css
- frontend/src/pages/CleanupPlans.test.tsx
- frontend/src/pages/CleanupPlans.tsx
- frontend/src/pages/Dashboard.tsx
- frontend/src/pages/Projects.tsx
- frontend/src/pages/ScanWorkspace.test.tsx
- frontend/src/pages/ScanWorkspace.tsx
- frontend/src/test/setup.ts
- frontend/tailwind.config.js
- frontend/vite.config.ts

### Existing untracked files

- DESIGN_PROPOSAL.md, IDEA.md
- frontend/src/components/AdaptiveView.tsx
- frontend/src/components/Sidebar.test.tsx, frontend/src/components/TopBar.test.tsx
- frontend/src/components/ui/Button.tsx, Card.tsx, DataTable.tsx, DataTable.test.tsx, EmptyState.tsx, ErrorAlert.tsx, ExpandableSection.tsx, LoadingState.tsx, RiskBadge.tsx, Stepper.tsx, Stepper.test.tsx
- frontend/src/context/ViewModeContext.tsx, frontend/src/design-tokens.ts
- frontend/src/pages/Dashboard.test.tsx, Projects.test.tsx
- frontend/src/utils/api.ts, api.test.ts

Git emitted line-ending normalization warnings for some modified frontend/backend files during diff inspection. No normalization was requested or performed.

## Architecture observed

- **Frontend:** React 18 + TypeScript + Vite + React Router. frontend/src/App.tsx routes Dashboard (/), Projects (/projects), Scan Workspace (/scan), Cleanup Plans (/plans), Cleanup History (/history), Restore (/restore), AI Agent (/agent), and Settings (/settings). DevSweepProvider holds the selected project, scan/cleanup histories, active plan, provider metadata, and activity flags in React memory. ViewModeProvider stores Simple/Technical mode in browser storage. Recent C1–C3.2 work adds shared UI components, theme tokens, adaptive views, responsive navigation and API error handling.
- **Backend:** FastAPI app in backend/main.py; scanner, cleanup, and AI routers are mounted under /api/scan, /api/cleanup, and /api/ai. Configuration is read by Pydantic Settings in backend/config.py; it checks repository-root .env and then backend/.env, with the latter taking precedence. No environment values or secrets were read for this baseline.
- **AI:** backend/ai/factory.py selects explicit demo/mock mode, a Nebius provider when NEBIUS_API_KEY is present, or a mock provider when no key is configured. Nebius uses the OpenAI-compatible AsyncOpenAI client in backend/ai/nebius_provider.py. The /api/ai/analyze route runs deterministic scanning, asks the provider for structured recommendations, validates returned paths against scanner candidates, and retains successful Nebius analysis data in an in-memory, one-use, same-project store with a 15-minute monotonic expiry.
- **Cleanup:** backend/cleanup/routes.py stores plans and protected-file pre-cleanup snapshots in process memory. CleanupEngine/FilesystemTools perform final allowlist, risk, protected-path, approval, and delete checks. Verification is implemented, but the stored verification snapshot is limited to protected-path existence booleans and is not a content backup.
- **Persistence:** DEVSWEEP_DB_PATH, SQLAlchemy and aiosqlite are present, but source search found no database engine/session/schema use. Plans, analysis authorization records, verification snapshots, selected projects, and cleanup history are process-memory or frontend-memory state; most Settings are browser-local only.

## Existing frontend/backend API contracts

These are the routes and shapes used by the current implementation and likely affected by security, persistence, restore, settings, and agent phases. Preserve compatibility or explicitly version/migrate any future changes.

| Endpoint | Current request and response contract | Current implementation / compatibility note |
| --- | --- | --- |
| GET /health | No body; status, version, ai_provider, ai_model, demo_mode | Calls provider factory; initialization errors can affect health response. |
| GET /api/config | No body; demo_mode, default_risk_level, workspace_root | Non-sensitive settings only. |
| POST /api/scan/ | {path?, include_hidden?, max_depth?} → project path/type/framework/package manager/language/git status, cleanup candidates (path, risk, reason, size_bytes, size_human), recoverable totals, protected paths, notes | Explicit outside-root paths are currently allowed: the root check catches ValueError and continues. include_hidden and max_depth appear in the request model; scanner route does not pass them to analyze_project. |
| GET /api/scan/demo | No body; same scan response shape | Uses repository demo-project fixture. |
| GET /api/scan/types | No body; supported project types and risk levels | Metadata endpoint. |
| POST /api/scan/demo/reset | No body; success/message | Runs repository generate_demo.py via subprocess. It is a mutating demo-fixture endpoint. Not called during Phase 0. |
| POST /api/ai/analyze | {project_path} → project metadata, candidates including deterministic scanner risk/AI risk/action/reason/size, recoverable total, ai_used, provider/model/demo flags, optional analysis_id | ai_used becomes true only after successful structured_completion when provider is NebiusProvider and demo mode is false. Mock responses remain identified as mock. Provider initialization, HTTP, rate-limit and inference errors produce HTTP errors rather than silently falling back for that request. |
| GET /api/ai/models | No body; current provider/model, demo flag and real_inference_available | Indicates configured provider state, not verified live Nebius connectivity. |
| POST /api/ai/chat | {message, history?, project_path?} → {response, suggestions} | Calls selected provider, including MockProvider. Response does not include per-response source metadata. Project context is a fresh scan summary, not scanner finding details or tool access. |
| POST /api/cleanup/plan | {project_path, analysis_id, items:[{path,action,risk,scanner_risk?,ai_risk?,effective_risk?,reason,estimated_bytes,regeneration_command?}], approved?} → plan ID, server-returned items/risks, totals, approval requirement, warnings, verification steps | Requires and consumes successful analysis ID for the same project. Server looks up selected paths in verified analysis and fresh scanner output; server analysis controls action/reason/size and scanner controls baseline risk. Request contract still accepts client risk/action fields, but route does not trust them as authoritative. |
| POST /api/cleanup/generate-plan | {project_path} → same plan response | Calls ai_analyze, requires successful Nebius inference and consumes the resulting verified analysis record. default_risk_level is a query parameter. |
| POST /api/cleanup/execute | {plan_id, approved?} → success, processed/deleted/failed counts, bytes freed, errors, duration | Uses in-memory stored plan; re-scans for candidates before CleanupEngine.execute_plan. It returns partial/failure information; HTTP 200 is not by itself proof all items were deleted. |
| POST /api/cleanup/verify | Backend reads {project_path, plan_id?} from JSON body; project_type is a separate query parameter. Returns {passed, checks, errors}. | **Frontend compatibility discrepancy:** CleanupPlans.tsx sends project_type inside the JSON body, so the backend currently uses its default query value "unknown". Backend plan/snapshot lookup remains in-memory. |
| GET /api/cleanup/plan/{plan_id} | No body; stored plan response | Implemented; current frontend does not call it. |

No backend routes were found for durable project/history retrieval, snapshot inventory/content restore, settings mutation, or AI agent tool execution. Frontend current API calls are /api/config, /api/ai/models, /api/scan/, /api/scan/demo, /api/ai/analyze, /api/ai/chat, /api/cleanup/plan, /api/cleanup/generate-plan, /api/cleanup/execute, and /api/cleanup/verify.

## Cleanup safety invariants and authorization flow

1. **Analysis authorization:** mock/demo analysis cannot authorize cleanup plans. Successful Nebius structured inference creates a server-side analysis ID. It expires after 15 minutes, is bound to the resolved project path, and is consumed once. Both plan routes require real inference; /generate-plan consumes its internally created record.
2. **Candidate and risk authority:** /cleanup/plan only accepts requested paths present in the verified server-side analysis and the fresh deterministic scanner result. Client-supplied action, risk, reason, and size do not override verified server data. Effective risk is the more restrictive of scanner and AI risk.
3. **DANGEROUS:** AI analysis forces scanner-DANGEROUS recommendations to KEEP. Cleanup engine rejects DANGEROUS delete candidates regardless of approval.
4. **CAUTION:** cleanup plan marks CAUTION deletion as requiring approval. Engine requires approved=true for any effective CAUTION delete. Frontend also requires explicit approval; backend remains authoritative.
5. **Execution validation:** execution references a server-held plan, freshly scans the project to produce an allowlist, validates current existence, exact scanner risk, protected paths and traversal through filesystem tools before deletion. No operation was executed in this baseline.
6. **Verification:** plan creation captures protected-file existence state; verification with a plan uses that state and fails closed if its snapshot is missing. This supports integrity checks for selected protected files, not restoration of deleted content.
7. **Important boundary gap:** scanner and cleanup plan routes deliberately allow explicit paths outside settings.workspace_root; AI analysis only checks path existence, and verification also accepts any existing path. Filesystem-level project-relative protections still apply within a chosen project, but this is not equivalent to enforcing one configured workspace boundary. main.py defaults BACKEND_HOST to 0.0.0.0 and backend has no authentication; CORS is not an access-control mechanism.

## Test baseline (cleanup-test caveat)

- Frontend command: npm test -- --reporter=dot from frontend/ — **53 tests passed across 9 files**. Initial sandbox run could not let esbuild read the parent workspace; rerun with workspace read access succeeded. Vitest emitted React Router future-flag warnings.
- Backend inventory: python -m pytest --collect-only -q from backend/ — **73 tests collected**.
- Backend command: .\.venv\Scripts\python.exe -m pytest -q -k "not actual_deleted_bytes_match_filesystem and not pre_cleanup_state_survives_execution_verification and not ai_safe_to_caution_upgrade_survives_execution and not missing_snapshot_fails_closed and not api_ai_safe_to_caution_workflow and not dangerous_never_deleted_even_with_approval and not caution_requires_approval and not authoritative_caution_requires_approval and not caution_approval_from_scanner_not_client and not protected_package_json_preserved and not protected_git_preserved and not protected_env_existed_missing_after_fails and not protected_env_never_existed_not_fail and not protected_env_protected and not execution and not approve" — **58 passed, 15 deselected**. The filter was intended to exclude cleanup execution tests, but it missed TestRiskDowngradeProtection.test_scanner_safe_client_safe_allowed, which invoked CleanupEngine.execute_plan and deleted a fixture directory inside a Python TemporaryDirectory. This was an accidental violation of the no-cleanup instruction. No demo-project, user project, or other persistent project data was targeted; the temporary fixture was automatically removed by the test context. I stopped backend test activity after identifying the miss. Pytest reported existing Pydantic deprecation and cache permission warnings.
- No frontend production build was requested for Phase 0 and none was run.

## Production-readiness phases and dependencies

The sequence below preserves the approved ordering: security and explicit boundaries precede durable cleanup records and restoration.

| Phase | Scope and main existing modules | Depends on / compatibility gate |
| --- | --- | --- |
| **0 — Baseline (this document)** | Capture dirty tree, contracts, safety rules, architecture and test baseline. | Complete; requires user review before Phase 1. |
| **1 — Security and workspace boundary** | backend/main.py, backend/config.py, scanner/AI/cleanup routes, backend/tools/filesystem.py, focused backend tests; default loopback bind, canonical configured-root validation, traversal/symlink defense, preserve protections and real-inference authorization. | First implementation phase. Decide local-only default and whether/how outside-root projects may be explicitly granted. Must not break request shapes without a migration path. |
| **2 — Durable records** | Existing SQLite config/dependencies; introduce repository/schema/migration modules and route integration for projects, plans, executions, verification, snapshot metadata. | After Phase 1 path/identity policy. Define DB location, backup/retention, migration policy, project identity, concurrency and recovery after interrupted execution. Existing in-memory API responses should remain compatible or be versioned. |
| **3 — Content-backed restore** | Filesystem snapshot service, cleanup execution integration, restore routes, Restore UI and tests. | Requires Phase 2 durable plan/execution IDs and safe Phase 1 path containment. Requires approval of snapshot size/retention, storage location, permissions, integrity algorithm, and restore conflict/overwrite behavior. Never report recoverable unless bytes are saved and verified. |
| **4 — Settings/configuration** | frontend/src/pages/Settings.tsx, config API and backend settings validation/storage, provider factory lifecycle. | Security baseline first. Decide mutable vs read-only fields, whether secrets can be entered in UI, secret storage mechanism, restart/apply semantics, and audit trail. Never return secrets. |
| **5 — AI Agent capabilities** | backend/ai/routes.py, provider abstraction, explicit scoped tool service/routes, frontend/src/pages/AIAgent.tsx. | Phase 1 boundary enforcement, Phase 2 durable identifiers as applicable. Define per-tool authorization and explicit confirmation for execution. Include provider/model source in each response; no AI-issued destructive operation without human confirmation. |
| **6 — UI controls and claims** | Restore/history/agent/settings UI, frontend/src/pages/RestoreCenter.tsx, CleanupHistory.tsx, AIAgent.tsx, Settings.tsx, shared UI utilities and repository link. | Backend functionality must exist before labels claim it. Implement Copy/Download and documentation navigation or clearly disable/remove claims. Depends on API contracts from earlier phases. |

## Risks, compatibility concerns, and decisions before Phase 1

1. **Workspace-root semantics:** should an explicit user-selected path outside the configured root be rejected outright, or allowed only through a separate explicit grant? The current API behavior permits outside-root paths; silently tightening it can break workflows.
2. **Local-only deployment:** approve 127.0.0.1 as the default bind and decide whether remote/LAN binding should require an explicit opt-in and warning. Without authentication, non-loopback operation is a high-risk exposure.
3. **Canonical path/symlink policy:** decide how to treat a project root that itself is a symlink, in-root symlink pointing outside, junctions/reparse points on Windows, and path changes between scan/plan/execute. Boundary checks must use canonical paths at each stage and maintain race-resistant validation.
4. **API compatibility:** /api/cleanup/verify frontend currently posts project_type in JSON while backend expects query parameter. Decide to fix frontend to query form or accept body compatibly; avoid unrelated contract redesign. /api/scan/ includes include_hidden/max_depth fields that currently have no effect; decide whether to implement or deprecate them later.
5. **Persistence and recovery:** SQLite dependencies/config are unused. Approve DB path/backup policy, retention, migrations, behavior when DB is locked/corrupt, and whether in-flight executions become resumable or terminally interrupted after restart.
6. **Restore policy:** no actual content snapshot exists. Approve snapshot storage location outside cleanup candidates, disk quota/retention, encryption expectations, integrity format, and safe behavior for files changed since cleanup. Metadata-only verification snapshots must not be described as file backups.
7. **Settings and secrets:** Settings currently stores broad values in localStorage; backend API only exposes read-only non-secret config. Approve which settings are truly runtime-configurable, secret input/storage policy, and when provider changes take effect. Existing environment credentials must remain untouched.
8. **AI tool authority:** chat currently has no tools but its welcome copy implies scan/plan/execute/restore capabilities. Decide exact permission model, confirmation UX and whether scan/plan tools may operate only on the selected project.
9. **Coverage boundary:** 15 backend tests were intentionally skipped because they execute filesystem deletions. Before later cleanup-related releases, authorize a separate isolated temporary-directory execution test run, still never using demo-project or user project paths.

## Phase 0 completion status

Baseline inspection and permitted tests are complete. No implementation phase has started. Await user review/approval before Phase 1.
