# DevSweep AI — Phase 1 Security and Workspace Boundary Report

**Scope:** Phase 1 only. No Phase 2 persistence, Phase 3 content restoration, authentication, or UI redesign was started. The previous pushed baseline commit remains unchanged; Phase 1 changes are uncommitted and unstaged.

## Implementation

- Added centralized canonical project authorization in backend/security/workspace_access.py. It resolves strict existing directory paths, rejects parent traversal and Windows drive-relative syntax, and captures directory identity from device/file index and birth time where available. In-root access is accepted only when the canonical target remains within DEVSWEEP_WORKSPACE_ROOT. Symlink and junction aliases resolve before authorization; an alias to an outside target requires a grant bound to that exact canonical directory.
- Added explicit external-folder grant/revoke routes in backend/security/routes.py: POST /api/access/grants and DELETE /api/access/grants/{grant_id}. A grant is an opaque random capability scoped to one canonical folder, expires after one hour, is capped at 256 active grants, and is held in process memory. Broad locations (filesystem root, home/root ancestors, workspace ancestors, and selected system/temp roots) are refused. Revocation, expiry, move, or directory identity change invalidates authorization. Backend restart revokes all grants; this is intentional until durable Phase 2 storage.
- Applied authorization to scan, AI analysis, project-context chat, both plan-generation routes, plan lookup, execution, verification, and the demo scan/reset paths. Successful AI analysis keeps the authorization alongside its one-use analysis record. Cleanup plans retain their authorization; execution revalidates before scanning and immediately before each deletion. Existing scanner allowlisting, real Nebius gating, risk escalation, DANGEROUS blocking, CAUTION approval, protected-path checks, and filesystem containment remain active.
- Changed backend default binding to 127.0.0.1. Configuration rejects non-loopback BACKEND_HOST and non-loopback FRONTEND_URL values. The ASGI middleware also rejects HTTP requests received on a wildcard or non-loopback listener if a server runner bypasses the setting. CORS is limited to local origins, credentials are disabled, and CORS is documented as non-authentication.
- Fixed the frontend verification contract: project_type is now sent as the backend’s query parameter, while project_path, plan_id, and optional access_grant_id remain in the JSON body.
- Frontend request state forwards an optional access_grant_id already present in a scan result through scan selection, AI analysis/chat, generation, and verification. No grant-creation UI was added.

## Files changed

- .env.example
- README.md
- backend/ai/routes.py
- backend/cleanup/engine.py
- backend/cleanup/routes.py
- backend/config.py
- backend/main.py
- backend/scanner/routes.py
- backend/security/__init__.py (new)
- backend/security/routes.py (new)
- backend/security/workspace_access.py (new)
- backend/tests/test_detector.py
- backend/tests/test_workspace_access.py (new)
- frontend/src/pages/AIAgent.tsx
- frontend/src/pages/CleanupPlans.test.tsx
- frontend/src/pages/CleanupPlans.tsx
- frontend/src/pages/Projects.tsx
- frontend/src/pages/ScanWorkspace.test.tsx
- frontend/src/pages/ScanWorkspace.tsx
- frontend/src/types/api.ts
- DEVSWEEP_PHASE1_REPORT.md (this report)

No actual .env file was opened for inspection or modified, and no credential was displayed. .env.example now uses the loopback default and contains no actual key. The production build generated ignored frontend/dist output; it was not staged or cleaned.

## API compatibility

| Contract | Before | After |
| --- | --- | --- |
| Scan | POST /api/scan/ accepted a path without workspace enforcement. | Existing body remains valid. Optional access_grant_id enables an explicitly granted external folder. Response additively returns the grant ID for that authorized external project. |
| AI analyze/chat | project_path alone was accepted. | Existing in-root calls remain valid. Optional access_grant_id is required for external project context. |
| Cleanup plan | /api/cleanup/plan used the successful analysis ID; /generate-plan accepted project_path. | Existing in-root request shapes work. Analysis ID is still the authority for /plan; /generate-plan accepts optional access_grant_id. Both revalidate authorization server-side. |
| Execute | plan_id and approved were accepted. | Request contract unchanged. Authorization is revalidated from server-held plan state, including grant revocation and directory identity. |
| Verify | Backend expected project_type in query, but frontend sent it in JSON. | Frontend now sends project_type in query. JSON includes path, plan ID, and optional grant ID. |
| External grants | No grant endpoints. | Added POST /api/access/grants and DELETE /api/access/grants/{grant_id}; grants expire after one hour and are memory-only. |
| Demo endpoints | Fixed demo path bypassed workspace authorization. | Demo scan/reset use the same project authorization policy. If outside configured root, an exact folder grant is required. Reset still regenerates only the fixed demo fixture when explicitly called. |

The existing UI does not yet expose external-grant creation or revocation. Users/integrations can use the backend OpenAPI/API endpoints; the ordinary in-workspace UI path remains compatible. This is a usability limitation, not an authorization bypass.

## Security decisions

- The configured workspace is the default authority. An external grant is created only by an explicit local API request and applies to one exact canonical directory; the raw path itself does not authorize subsequent access.
- External grants are deliberately ephemeral and nonpersistent. This avoids a partial storage system before Phase 2. Restart revokes them; expiration is one hour; revocation is immediate. Folder movement or replacement requires a new grant.
- Backend remote/LAN use is disabled. CORS is a browser-origin restriction, not authentication. Do not expose this local application through an unauthenticated reverse proxy.
- File-content snapshots/restoration are not implemented. Phase 3 remains required before any claim of deleted-file recovery.

## Test and build results

- Backend: .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider — **87 passed**, 1 existing Pydantic deprecation warning. Tests that execute cleanup were reviewed: targets are disposable TemporaryDirectory/pytest temporary fixtures only. No test targeted the repository, demo-project, or a user project.
- Focused junction/symlink escape and replacement test: **1 passed** using a temporary Windows junction after native symlink creation was unavailable.
- Frontend full suite: npm test -- --reporter=dot — **53 passed across 9 files**.
- Frontend affected tests after the grant forwarding and verify-contract assertions: npm test -- --reporter=dot src/pages/CleanupPlans.test.tsx src/pages/ScanWorkspace.test.tsx — **28 passed across 2 files**.
- Production build: npm run build — **passed** (TypeScript and Vite production build).
- Diff whitespace check: git diff --check — **passed**.

No real cleanup operation was run manually. Backend tests that invoke deletion did so only inside their reviewed temporary test fixtures, which are removed by their temporary-directory context.

## Remaining limitations

1. The existing frontend has no explicit grant creation/revocation screen or input. External-folder use currently requires the local API/OpenAPI grant flow; Phase 1 did not redesign the UI.
2. Grants and plans remain in memory and are lost at backend restart. Durable project/plan/execution/verification records remain Phase 2 work.
3. The built-in demo scan/reset may require a grant if demo-project is outside the configured workspace. The demo reset endpoint remains intentionally mutating when explicitly authorized and invoked.
4. Remote/LAN access is unsupported until authentication and appropriate remote security controls are designed.
5. The existing Pydantic class-based config deprecation warning remains outside Phase 1 scope.

## Completion

Phase 1 implementation and isolated verification are complete. No Phase 2 or Phase 3 work was started. The Git-visible working changes are only the Phase 1 files listed above; nothing was committed or pushed.
