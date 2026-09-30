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
3. **Analyze** what's safe to remove vs. what must be protected
4. **Plan** a cleanup with risk levels and explanations
5. **Ask** for your approval before any destructive action
6. **Execute** approved cleanup safely
7. **Verify** the project still works
8. **Remember** the project state for future restoration

## Architecture

```
DevSweep AI
├── Frontend (React + Vite + Tailwind)
│   ├── Dashboard - Storage overview, project cards, scan CTA
│   ├── Projects - Manage multiple projects
│   ├── Scan Workspace - Interactive scanning
│   ├── Cleanup Plans - Review and approve plans
│   ├── Cleanup History - Audit trail
│   ├── Restore Center - Reconstruct environments
│   ├── AI Agent - Chat interface for natural language requests
│   └── Settings - Configuration
│
├── Backend (Python + FastAPI)
│   ├── AI Agent (Nebius Token Factory + NVIDIA Nemotron)
│   ├── Project Scanner (detect type, framework, dependencies)
│   ├── Cleanup Engine (safety rules, risk assessment)
│   ├── Restore Engine (reconstruct environments)
│   ├── Project Memory (lightweight manifests)
│   └── Tools (filesystem, git, subprocess with allowlists)
│
└── Demo Project Fixture
    ├── Deterministic 2+ GB recoverable demo
    └── Clearly separated from production mode
```

## AI Workflow

```
OBSERVE → UNDERSTAND → ANALYZE → PLAN → ASK APPROVAL → EXECUTE → VERIFY → REMEMBER → RESTORE
```

The AI **recommends**, the application **validates**, the user **approves**, the application **executes**.

## Safety Model

- **SAFE** - Regenerable artifacts (node_modules, dist, __pycache__, .venv)
- **CAUTION** - Project-specific caches, unknown directories
- **DANGEROUS** - Source code, Git history, .env files, credentials, databases

Default: **SAFE cleanup only**. Explicit confirmation required for CAUTION.

## Nebius + NVIDIA Integration

This project is built for the **Nebius x NVIDIA Global AI Hackathon**.

- **Nebius Token Factory** provides the OpenAI-compatible API endpoint
- **NVIDIA Nemotron** models provide the reasoning capability
- Real runtime calls to Nebius Token Factory (not mocked in demo)
- AI provider abstraction allows swapping providers for other hackathons

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your NEBIUS_API_KEY
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEBIUS_API_KEY` | Nebius Token Factory API key | For AI features |
| `NEBIUS_BASE_URL` | API base URL (default: https://api.studio.nebius.ai/v1) | No |
| `NEBIUS_MODEL` | Model name (default: nemotron-3-ultra) | No |
| `DEVSWEEP_WORKSPACE_ROOT` | Root directory to scan (default: current dir) | No |
| `DEVSWEEP_DEMO_MODE` | Enable demo fixture (true/false) | No |

## Demo Mode

Run with a deterministic demo project that shows 2+ GB recoverable without a real project:

```bash
DEVSWEEP_DEMO_MODE=true uvicorn main:app --reload
```

## Project Structure

```
DevSweepAI/
├── backend/
│   ├── ai/                 # AI provider abstraction, Nebius client, prompts, agent
│   ├── scanner/            # Project detection, framework detection, dependency analysis
│   ├── cleanup/            # Cleanup candidates, risk assessment, execution, verification
│   ├── restore/            # Restore logic per ecosystem
│   ├── memory/             # Project manifest, history storage
│   ├── tools/              # Filesystem, git, subprocess tools with allowlists
│   ├── tests/              # Unit and integration tests
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Configuration management
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API clients
│   │   ├── context/        # React context providers
│   │   └── types/          # TypeScript types
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── demo-project/           # Deterministic demo fixture
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   └── DEMO.md
├── .gitignore
├── .env.example
└── LICENSE
```

## License

MIT License - see [LICENSE](LICENSE) for details.