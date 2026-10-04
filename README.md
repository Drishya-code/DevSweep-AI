# DevSweep AI

> **Clean your workspace. Keep your project. Restore it anytime.**
DevSweep AI is an intelligent developer workspace management tool that helps you reclaim storage space from regenerable artifacts (node_modules, build outputs, caches, virtual environments) while keeping your source code, Git history, and project configuration safe.

## Problem

Development projects accumulate massive amounts of regenerable files:
- `node_modules` (often 1-2 GB)
- Python virtual environments (100-500 MB)
- Build/dist folders
- Package manager caches
- Compiler caches
- Logs and temporary files
- IDE caches

Manually identifying what's safe to delete is error-prone and time-consuming.

## Solution

DevSweep AI uses an **agentic AI workflow** to:
1. **Scan** your workspace intelligently
2. **Understand** your project type, dependencies, and structure
3. **Analyze** what's safe to remove vs. what must be protected (via NVIDIA Nemotron)
4. **Plan** a cleanup with risk levels and explanations
5. **Ask** for your approval before any destructive action
6. **Execute** approved cleanup safely
7. **Verify** the project still works

## Architecture

```
DevSweep AI
├── Frontend (React + Vite + Tailwind)
│   ├── Dashboard - Storage overview, project cards, scan CTA
│   ├── Projects - Manage multiple projects
│   ├── Scan Workspace - Interactive scanning
│   ├── Cleanup Plans - Review and approve plans
│   ├── Cleanup History - Audit trail (Preview - not persisted)
│   ├── Restore Center - Reconstruct environments (Preview - not executed)
│   ├── AI Agent - Chat interface for natural language requests
│   └── Settings - Configuration (no API key storage)
│
├── Backend (Python + FastAPI)
│   ├── AI Agent (Nebius Token Factory + NVIDIA Nemotron)
│   ├── Project Scanner (detect type, framework, dependencies, real git status)
│   ├── Cleanup Engine (safety rules, risk assessment, scanner allowlist enforcement)
│   ├── Verification Engine (project health after cleanup, pre-cleanup state tracking)
│   └── Tools (filesystem, git with protection allowlists)
│
└── Demo Project Fixture
     ├── ~128 MB of real generated files (deterministic seed)
     └── Regenerated on demand via /api/scan/demo/reset
```

## AI Workflow

```
FILESYSTEM SCAN
      ↓
DETERMINISTIC CANDIDATES
      ↓
STRUCTURED CANDIDATE CONTEXT
      ↓
NVIDIA NEMOTRON VIA NEBIUS
      ↓
STRUCTURED AI RECOMMENDATIONS
      ↓
DETERMINISTIC SAFETY VALIDATION
      ↓
CLEANUP PLAN
      ↓
USER APPROVAL
      ↓
EXECUTION
```

The AI **recommends**, the application **validates**, the user **approves**, the application **executes**. The AI never executes deletion directly.

### Safety Rules for AI Recommendations

- AI recommendations for paths **not discovered by the scanner are rejected**
- If AI upgrades SAFE → CAUTION, the higher (more restrictive) classification wins
- AI can never downgrade risk
- **DANGEROUS → DELETE is always rejected**
- Only SAFE and CAUTION items can be deleted; CAUTION requires explicit user approval

## Safety Model

- **SAFE** - Regenerable artifacts (node_modules, dist, __pycache__, .venv)
- **CAUTION** - Project-specific caches, unknown large directories
- **DANGEROUS** - Source code, Git history, .env files, credentials, databases

Default: **SAFE cleanup only**. Explicit confirmation required for CAUTION.

### Deletion Allowlist

A DELETE target must satisfy ALL of:
1. It is inside the project workspace (no path traversal, nothing outside)
2. It is not protected (source code, .git, .env, credentials, config files)
3. It was discovered by the deterministic scanner
4. It is classified as SAFE or CAUTION (never DANGEROUS)
5. CAUTION requires explicit user approval

The server re-validates every deletion target against a fresh scanner run at execution time. Client-supplied risk/size/reason values are never trusted as authoritative.

## Nebius + NVIDIA Integration

This project is built for the **Nebius x NVIDIA Global AI Hackathon**.

- **Nebius Token Factory** endpoint: `https://api.tokenfactory.us-central1.nebius.com/v1/`
- **Model**: `nvidia/nemotron-3-super-120b-a12b`
- Real runtime calls to Nebius Token Factory in the analysis and chat endpoints
- AI provider abstraction (NebiusProvider / MockProvider) — mock is used only when no API key is configured

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
# Set your NEBIUS_API_KEY in the environment (see .env.example)
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEBIUS_API_KEY` | Nebius Token Factory API key | For real AI analysis |
| `NEBIUS_BASE_URL` | API base URL (default: https://api.tokenfactory.us-central1.nebius.com/v1/) | No |
| `NEBIUS_MODEL` | Model name (default: nvidia/nemotron-3-super-120b-a12b) | No |
| `DEVSWEEP_WORKSPACE_ROOT` | Root directory to scan (default: current dir) | No |
| `DEVSWEEP_DB_PATH` | SQLite application-history file (default: `./data/devsweep.db`, relative to the configured workspace root) | No |
| `DEVSWEEP_BACKUP_ROOT` | Verified content-backup directory (default: per-user application data directory; must be outside scanned project trees) | No |
| `DEVSWEEP_DEMO_MODE` | Enable demo fixture (true/false) | No |
| `BACKEND_HOST` | Loopback bind address (default: `127.0.0.1`; non-loopback values are rejected until remote authentication exists) | No |

## Demo Mode

The demo project fixture is generated locally with a fixed random seed (deterministic), producing ~128 MB of real files across 7 cleanup candidates:

```bash
python generate_demo.py          # generate/reset demo data
uvicorn main:app --reload        # from backend/
# POST /api/scan/demo/reset also regenerates on demand
```

## Local Workspace Security

The backend is local-first and binds to `127.0.0.1` by default. `BACKEND_HOST` accepts only `localhost` or a loopback IP address. Non-loopback/LAN binding is rejected because this application does not provide remote authentication. CORS restricts browser origins to local development origins; CORS is not authentication or authorization.

Project paths are canonicalized by the backend. Paths inside `DEVSWEEP_WORKSPACE_ROOT` need no separate grant. External folders require an explicit, folder-scoped grant created by the local user through `POST /api/access/grants`.

The response contains an opaque `grant_id`. Pass it as `access_grant_id` with project scan, AI analysis/chat, and direct plan-generation requests. A successful AI analysis binds its one-use analysis authorization to the same project and grant. Verification accepts the grant ID in its JSON body; execution revalidates the authorization retained with the plan. Revoke a grant with `DELETE /api/access/grants/{grant_id}`. A grant is scoped to one canonical directory, expires after one hour, is invalidated if that directory identity changes, and is held only in process memory; backend restart revokes all grants.

The built-in UI does not yet provide grant creation/revocation controls. External-folder access is available through the backend API/OpenAPI interface; the ordinary in-workspace UI flow is unchanged. Demo scanning/reset also observes the workspace boundary; if the fixed demo folder is outside the configured root, explicitly grant that exact folder first. `/api/scan/demo/reset` regenerates demo fixture data and should only be invoked intentionally.

## Persistent History

Projects, successful scan summaries, cleanup plans/items, execution outcomes, protected-file existence metadata, verification results, content-backup manifests, and restore outcomes are stored in the SQLite database configured by `DEVSWEEP_DB_PATH`. The backend runs versioned schema initialization at startup. Existing databases are inspected and backed up with SQLite's backup API before schema upgrades; ambiguous/incompatible schemas fail startup without being modified. External access grants and one-use AI analysis authorizations are never stored. Historical cleanup plans are review-only after a restart and cannot authorize execution. Protected-file metadata records existence checks only; this is not a content backup and does not make files recoverable.

### Content backups and restoration

Before deleting an approved `SAFE` item, or a `CAUTION` item with explicit approval, the backend saves its file contents under `DEVSWEEP_BACKUP_ROOT` and verifies a SHA-256 manifest. The default is `%LOCALAPPDATA%/DevSweepAI/backups` on Windows and the user's application-data directory on other platforms. Configure an alternate location only when it is outside every project tree that may be scanned or cleaned. Backups are not automatically pruned; manage their storage deliberately. Candidates containing symlinks, junctions, reparse points, unsupported objects, or changed content fail closed and are not deleted.

The Restore Center lists only verified backups whose corresponding cleanup outcome is recorded complete. Restoration requires the same currently authorized project identity and explicit confirmation. Existing destinations are never overwritten. Directory restores can be partial if the filesystem fails mid-write; those outcomes are recorded and must be inspected before retrying. Backup manifests retain content hashes, sizes, relative paths, file mode, and modification time; ownership and platform-specific ACLs are not preserved. Backup contents are not encrypted by DevSweep; the default Windows location inherits the current user's application-data permissions. Backups contain real project data and should be protected like the original workspace. Do not configure a shared or untrusted backup location.

## Project Structure

The API also denies requests if a server runner bypasses the host setting and exposes a wildcard/non-loopback listener. Do not place an unauthenticated remote reverse proxy in front of the backend.

```
DevSweepAI/
├── backend/
│   ├── ai/                 # AI provider abstraction, Nebius client, prompts, routes
│   ├── scanner/            # Project detection, framework detection, candidates
│   ├── cleanup/            # Cleanup engine, plan generator, verification
│   ├── tools/              # Filesystem/git tools with protection allowlists
│   ├── persistence/        # Versioned SQLite history schema and repositories
│   ├── tests/              # Unit + integration tests
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Configuration management
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── context/        # React context providers
│   │   └── types/          # TypeScript types
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── demo-project/           # Demo fixture (generated locally, gitignored)
├── generate_demo.py        # Deterministic demo data generator
├── .gitignore
├── .env.example
└── LICENSE
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check with AI provider status |
| POST | `/api/access/grants` | Grant temporary access to one external project folder |
| DELETE | `/api/access/grants/{grant_id}` | Revoke a folder grant |
| POST | `/api/scan/` | Scan a workspace path |
| GET | `/api/scan/demo` | Scan the demo project |
| POST | `/api/scan/demo/reset` | Regenerate demo data |
| POST | `/api/ai/analyze` | AI analysis (scan → Nemotron → validated recommendations) |
| POST | `/api/ai/chat` | Chat with the AI agent |
| GET | `/api/ai/models` | Current AI provider/model info |
| POST | `/api/cleanup/generate-plan` | Generate cleanup plan (AI-validated) |
| POST | `/api/cleanup/execute` | Execute approved plan (with scanner allowlist re-validation) |
| POST | `/api/cleanup/verify` | Verify project health after cleanup |
| GET | `/api/cleanup/history/projects` | Persistent project metadata and current path availability |
| GET | `/api/cleanup/history/scans` | Persistent successful scan history |
| GET | `/api/cleanup/history/plans` | Historical plans, always review-only through this endpoint |
| GET | `/api/cleanup/history/executions` | Persistent execution outcomes and verification metadata |
| GET | `/api/cleanup/history/summary` | Persistent record counts for the dashboard |
| GET | `/api/cleanup/backups` | Verified backup items from completed cleanup operations |
| POST | `/api/cleanup/restore` | Restore one verified item (requires project path and explicit approval) |
| GET | `/api/cleanup/restore/history` | Persistent restore outcomes |

## License

MIT License - see [LICENSE](LICENSE) for details.
