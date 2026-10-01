"""AI Agent API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json

from ai.factory import get_ai_provider
from ai.prompts import DEVSWEEP_SYSTEM_PROMPT
from scanner.detector import analyze_project, RiskLevel
from config import settings
from pathlib import Path


router = APIRouter(tags=["ai"])


class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    project_path: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []


class AnalyzeRequest(BaseModel):
    project_path: str


class AnalyzeResponse(BaseModel):
    project_type: str
    framework: str
    package_manager: str
    language: str
    candidates: List[Dict[str, Any]]
    total_recoverable: int
    total_recoverable_human: str


def format_bytes(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(request: ChatRequest):
    """Chat with the AI agent."""
    provider = get_ai_provider()
    
    # Build context - convert to provider ChatMessage format
    from ai.provider import ChatMessage as ProviderChatMessage
    
    messages = [
        ProviderChatMessage(role="system", content=DEVSWEEP_SYSTEM_PROMPT),
    ]
    
    # Add project context if provided
    if request.project_path:
        path = Path(request.project_path)
        if path.exists():
            try:
                analysis = analyze_project(path)
                context = f"""
Current project: {path}
Type: {analysis.project_type.value}
Framework: {analysis.framework}
Package manager: {analysis.package_manager}
Language: {analysis.language}
Git: {analysis.has_git} (clean: {analysis.git_clean})
Cleanup candidates: {len(analysis.cleanup_candidates)}
Total recoverable: {format_bytes(analysis.total_recoverable_bytes)}
"""
                messages.append(ProviderChatMessage(role="system", content=context))
            except Exception:
                pass
    
    # Add history
    for msg in request.history[-10:]:  # Keep last 10 messages
        messages.append(ProviderChatMessage(role=msg.role, content=msg.content))
    
    # Add current message
    messages.append(ProviderChatMessage(role="user", content=request.message))
    
    try:
        response = await provider.chat_completion(messages)
        return ChatResponse(
            response=response.content,
            suggestions=response.suggestions if hasattr(response, 'suggestions') else [],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def ai_analyze(request: AnalyzeRequest):
    """Analyze a project with AI."""
    path = Path(request.project_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project path not found")
    
    # First, run deterministic scan
    analysis = analyze_project(path)
    
    # Build structured candidate context for Nemotron
    candidate_context = []
    for c in analysis.cleanup_candidates:
        candidate_context.append({
            "path": c.path,
            "size_bytes": c.size_bytes,
            "scanner_risk": c.risk.value,
            "scanner_reason": c.reason,
        })
    
    # Call Nemotron for AI analysis
    provider = get_ai_provider()
    from ai.provider import ChatMessage as ProviderChatMessage
    
    # Create structured prompt for Nemotron
    system_prompt = """You are DevSweep AI, analyzing developer workspace cleanup candidates.
You receive deterministic scanner findings and must provide structured recommendations.

For each candidate, respond with:
- path: the exact path from the scanner
- action: "DELETE" or "KEEP"
- risk: "SAFE", "CAUTION", or "DANGEROUS" 
- reason: concise explanation

Rules:
1. Never recommend DANGEROUS items for deletion
2. If scanner says SAFE but you see risk, upgrade to CAUTION (never downgrade)
3. Only recommend paths that were in the scanner results
4. Return valid JSON only"""
    
    user_prompt = f"""Project Analysis:
- Path: {path}
- Type: {analysis.project_type.value}
- Framework: {analysis.framework}
- Package Manager: {analysis.package_manager}
- Language: {analysis.language}
- Git: {analysis.has_git} (clean: {analysis.git_clean})

Scanner Candidates ({len(candidate_context)} items):
{json.dumps(candidate_context, indent=2)}

Return JSON:
{{
  "recommendations": [
    {{"path": "...", "action": "DELETE|KEEP", "risk": "SAFE|CAUTION|DANGEROUS", "reason": "..."}}
  ]
}}"""
    
    messages = [
        ProviderChatMessage(role="system", content=system_prompt),
        ProviderChatMessage(role="user", content=user_prompt),
    ]
    
    ai_recommendations = []
    try:
        response = await provider.structured_completion(
            messages=messages,
            schema={
                "type": "object",
                "properties": {
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "action": {"type": "string", "enum": ["DELETE", "KEEP"]},
                                "risk": {"type": "string", "enum": ["SAFE", "CAUTION", "DANGEROUS"]},
                                "reason": {"type": "string"},
                            },
                            "required": ["path", "action", "risk", "reason"],
                        },
                    }
                },
                "required": ["recommendations"],
            },
        )
        ai_recommendations = response.get("recommendations", [])
    except Exception as e:
        # Fallback to scanner recommendations if AI fails
        ai_recommendations = [
            {
                "path": c.path,
                "action": "DELETE" if c.risk in (RiskLevel.SAFE, RiskLevel.CAUTION) else "KEEP",
                "risk": c.risk.value,
                "reason": c.reason + " (fallback - AI unavailable)",
            }
            for c in analysis.cleanup_candidates
        ]
    
    # Merge AI recommendations with scanner results (safety validation)
    # Only use AI recommendations for paths that exist in scanner results
    scanner_paths = {c.path: c for c in analysis.cleanup_candidates}
    final_candidates = []
    
    for ai_rec in ai_recommendations:
        path = ai_rec.get("path", "")
        if path not in scanner_paths:
            # Reject unknown paths
            continue
        
        scanner_candidate = scanner_paths[path]
        
        # Scanner risk remains authoritative for validation
        scanner_risk = scanner_candidate.risk.value
        ai_risk = ai_rec.get("risk", "SAFE")
        
        # Reject DANGEROUS deletions based on scanner risk
        action = ai_rec.get("action", "KEEP")
        if scanner_risk == "DANGEROUS" and action == "DELETE":
            action = "KEEP"
        
        final_candidates.append({
            "path": path,
            "risk": scanner_risk,  # Deterministic scanner risk (authoritative for validation)
            "ai_risk": ai_risk,    # AI-assessed risk (can be higher, used for approval)
            "reason": ai_rec.get("reason", scanner_candidate.reason),
            "size_bytes": scanner_candidate.size_bytes,
            "size_human": format_bytes(scanner_candidate.size_bytes),
            "action": action,
        })
    
    total_recoverable = sum(c["size_bytes"] for c in final_candidates if c["action"] == "DELETE" and c["risk"] in ("SAFE", "CAUTION"))

    return AnalyzeResponse(
        project_type=analysis.project_type.value,
        framework=analysis.framework,
        package_manager=analysis.package_manager,
        language=analysis.language,
        candidates=final_candidates,
        total_recoverable=total_recoverable,
        total_recoverable_human=format_bytes(total_recoverable),
    )


@router.get("/models")
async def get_models():
    """Get available AI models."""
    provider = get_ai_provider()
    return {
        "current": provider.model_name if hasattr(provider, 'model_name') else "unknown",
        "provider": provider.__class__.__name__,
    }