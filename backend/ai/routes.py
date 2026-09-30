"""AI Agent API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid

from ai.factory import get_ai_provider
from ai.prompts import DEVSWEEP_SYSTEM_PROMPT
from scanner.detector import analyze_project
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
    
    analysis = analyze_project(path)
    
    return AnalyzeResponse(
        project_type=analysis.project_type.value,
        framework=analysis.framework,
        package_manager=analysis.package_manager,
        language=analysis.language,
        candidates=[
            {
                "path": c.path,
                "risk": c.risk.value,
                "reason": c.reason,
                "size_bytes": c.size_bytes,
                "size_human": format_bytes(c.size_bytes),
            }
            for c in analysis.cleanup_candidates
        ],
        total_recoverable=analysis.total_recoverable_bytes,
        total_recoverable_human=format_bytes(analysis.total_recoverable_bytes),
    )


@router.get("/models")
async def get_models():
    """Get available AI models."""
    provider = get_ai_provider()
    return {
        "current": provider.model_name if hasattr(provider, 'model_name') else "unknown",
        "provider": provider.__class__.__name__,
    }