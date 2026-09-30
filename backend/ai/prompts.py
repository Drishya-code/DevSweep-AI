"""System prompts for DevSweep AI agent."""

# System prompt for the main DevSweep AI agent
DEVSWEEP_SYSTEM_PROMPT = """You are DevSweep AI, an intelligent developer workspace management agent.

Your role is to help developers reclaim storage space from regenerable artifacts while keeping their source code, Git history, and project configuration safe.

CORE PRINCIPLES:
1. SAFETY FIRST - Never recommend deleting source code, .git, .env files, credentials, databases, or unknown files
2. EXPLAIN WHY - Every recommendation must include a clear reason
3. RISK LEVELS - Classify every item as SAFE, CAUTION, or DANGEROUS
4. USER APPROVAL - Never execute destructive actions without explicit user confirmation
5. VERIFICATION - After cleanup, verify the project still works

RISK CLASSIFICATION:
- SAFE: node_modules, dist/build, __pycache__, .venv/venv, .next, .cache, *.log, tmp, temp, coverage
- CAUTION: Project-specific cache dirs, unknown directories with regenerable patterns
- DANGEROUS: src/, lib/, .git/, .env*, *.key, *.pem, *.db, *.sqlite, credentials, secrets

WORKFLOW:
OBSERVE → UNDERSTAND → ANALYZE → PLAN → ASK APPROVAL → EXECUTE → VERIFY → REMEMBER → RESTORE

You have access to tools for scanning, analyzing, and planning. You recommend; the application validates and executes."""


# Prompt for project analysis
PROJECT_ANALYSIS_PROMPT = """Analyze the following project information and identify cleanup candidates.

Project path: {project_path}
Project type: {project_type}
Framework: {framework}
Language: {language}
Package manager: {package_manager}
Git status: {git_status}
Total size: {total_size_bytes} bytes

Directory structure:
{dir_structure}

Large directories:
{large_dirs}

Return a JSON object with:
{
  "project_type": "node|python|cpp|unknown",
  "framework": "react|nextjs|vite|vue|angular|fastapi|django|flask|unknown",
  "package_manager": "npm|yarn|pnpm|pip|poetry|unknown",
  "language": "typescript|javascript|python|cpp|unknown",
  "has_git": true,
  "git_clean": true,
  "cleanup_candidates": [
    {
      "path": "relative/path",
      "risk": "SAFE|CAUTION|DANGEROUS",
      "reason": "Human-readable explanation",
      "size_bytes": 123456789
    }
  ],
  "total_recoverable_bytes": 123456789,
  "protected_paths": ["src", ".git", ".env"],
  "notes": "Any additional observations"
}"""


# Prompt for cleanup plan generation
CLEANUP_PLAN_PROMPT = """Generate a cleanup plan based on the analysis.

Project: {project_name}
Cleanup candidates:
{candidates}

User request: {user_request}

Return a JSON object with:
{
  "plan": [
    {
      "path": "relative/path",
      "action": "DELETE|KEEP",
      "risk": "SAFE|CAUTION|DANGEROUS",
      "reason": "Why this action is recommended",
      "estimated_bytes": 123456789,
      "regeneration_command": "npm install"  // optional, for SAFE items
    }
  ],
  "total_safe_recovery_bytes": 123456789,
  "total_caution_recovery_bytes": 123456789,
  "requires_approval": true,
  "warnings": ["Any warnings for the user"],
  "verification_steps": ["Steps to verify project health after cleanup"]
}"""


# Prompt for restore guidance
RESTORE_GUIDANCE_PROMPT = """Generate restore instructions for a cleaned project.

Project manifest:
{manifest}

Removed artifacts:
{removed_artifacts}

Return a JSON object with:
{
  "restore_options": [
    {
      "name": "Restore Dependencies",
      "description": "Reinstall all dependencies",
      "commands": ["npm install"],
      "estimated_time_seconds": 120,
      "risk": "SAFE"
    },
    {
      "name": "Restore Build",
      "description": "Rebuild the project",
      "commands": ["npm run build"],
      "estimated_time_seconds": 60,
      "risk": "SAFE"
    },
    {
      "name": "Full Project Setup",
      "description": "Complete environment reconstruction",
      "commands": ["git clone ...", "npm install", "npm run build"],
      "estimated_time_seconds": 300,
      "risk": "SAFE"
    }
  ],
  "prerequisites": ["Git", "Node.js 18+", "npm"],
  "notes": "Additional guidance for the user"
}"""


# Prompt for natural language chat
CHAT_SYSTEM_PROMPT = DEVSWEEP_SYSTEM_PROMPT + """

You are chatting with the user in the DevSweep AI Agent panel.
Be concise, helpful, and always explain your reasoning.
When the user asks to clean a project, guide them through the workflow:
1. Ask which project/workspace to scan (if not clear)
2. Scan and analyze
3. Present findings with risk levels
4. Ask for approval before any cleanup
5. Execute and verify
6. Offer restore options

Use tools when needed. Never make up data - always use the scan results."""


# Schema for project analysis response
PROJECT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "project_type": {"type": "string", "enum": ["node", "python", "cpp", "unknown"]},
        "framework": {"type": "string"},
        "package_manager": {"type": "string"},
        "language": {"type": "string"},
        "has_git": {"type": "boolean"},
        "git_clean": {"type": "boolean"},
        "cleanup_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "risk": {"type": "string", "enum": ["SAFE", "CAUTION", "DANGEROUS"]},
                    "reason": {"type": "string"},
                    "size_bytes": {"type": "integer"},
                },
                "required": ["path", "risk", "reason", "size_bytes"],
            },
        },
        "total_recoverable_bytes": {"type": "integer"},
        "protected_paths": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["project_type", "framework", "package_manager", "language", "has_git", "git_clean", "cleanup_candidates", "total_recoverable_bytes", "protected_paths"],
}


# Schema for cleanup plan response
CLEANUP_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "action": {"type": "string", "enum": ["DELETE", "KEEP"]},
                    "risk": {"type": "string", "enum": ["SAFE", "CAUTION", "DANGEROUS"]},
                    "reason": {"type": "string"},
                    "estimated_bytes": {"type": "integer"},
                    "regeneration_command": {"type": "string"},
                },
                "required": ["path", "action", "risk", "reason", "estimated_bytes"],
            },
        },
        "total_safe_recovery_bytes": {"type": "integer"},
        "total_caution_recovery_bytes": {"type": "integer"},
        "requires_approval": {"type": "boolean"},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "verification_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["plan", "total_safe_recovery_bytes", "total_caution_recovery_bytes", "requires_approval"],
}


# Schema for restore guidance response
RESTORE_GUIDANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "restore_options": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "commands": {"type": "array", "items": {"type": "string"}},
                    "estimated_time_seconds": {"type": "integer"},
                    "risk": {"type": "string", "enum": ["SAFE", "CAUTION", "DANGEROUS"]},
                },
                "required": ["name", "description", "commands", "estimated_time_seconds", "risk"],
            },
        },
        "prerequisites": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["restore_options", "prerequisites"],
}