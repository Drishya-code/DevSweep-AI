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
| `DEVSWEEP_DEMO_MODE` | Enable demo fixture (true/false) | No |

## Demo Mode

The demo project fixture is generated locally with a fixed random seed (deterministic), producing ~128 MB of real files across 7 cleanup candidates:

```bash
python generate_demo.py          # generate/reset demo data
uvicorn main:app --reload        # from backend/
# POST /api/scan/demo/reset also regenerates on demand
```

## Project Structure

```
DevSweepAI/
├── backend/
│   ├── ai/                 # AI provider abstraction, Nebius client, prompts, routes
│   ├── scanner/            # Project detection, framework detection, candidates
│   ├── cleanup/            # Cleanup engine, plan generator, verification
│   ├── tools/              # Filesystem/git tools with protection allowlists
│   ├── tests/              # 40 unit + integration tests
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
| POST | `/api/scan/` | Scan a workspace path |
| GET | `/api/scan/demo` | Scan the demo project |
| POST | `/api/scan/demo/reset` | Regenerate demo data |
| POST | `/api/ai/analyze` | AI analysis (scan → Nemotron → validated recommendations) |
| POST | `/api/ai/chat` | Chat with the AI agent |
| GET | `/api/ai/models` | Current AI provider/model info |
| POST | `/api/cleanup/generate-plan` | Generate cleanup plan (AI-validated) |
| POST | `/api/cleanup/execute` | Execute approved plan (with scanner allowlist re-validation) |
| POST | `/api/cleanup/verify` | Verify project health after cleanup |

## License

MIT License - see [LICENSE](LICENSE) for details.