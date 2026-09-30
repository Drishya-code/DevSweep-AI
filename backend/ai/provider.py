from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import json


@dataclass
class AIResponse:
    content: str
    usage: Optional[dict] = None
    model: Optional[str] = None


@dataclass
class ChatMessage:
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def structured_completion(
        self,
        messages: list[ChatMessage],
        response_schema: dict,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict:
        """Send a structured completion request with JSON schema validation."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name."""
        pass


class MockProvider(AIProvider):
    """Mock provider for development and testing without API keys."""

    def __init__(self, model_name: str = "mock-model"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        # Return a deterministic mock response based on the last user message
        last_msg = messages[-1] if messages else None
        if last_msg and "scan" in last_msg.content.lower():
            content = json.dumps({
                "project_type": "node",
                "framework": "react",
                "package_manager": "npm",
                "cleanup_candidates": [
                    {"path": "node_modules", "risk": "SAFE", "reason": "Regenerable dependencies", "size_bytes": 1800000000},
                    {"path": "dist", "risk": "SAFE", "reason": "Build output", "size_bytes": 420000000},
                    {"path": ".vite", "risk": "SAFE", "reason": "Vite cache", "size_bytes": 86000000},
                ],
                "total_recoverable_bytes": 2306000000,
            })
        elif last_msg and "plan" in last_msg.content.lower():
            content = json.dumps({
                "plan": [
                    {"path": "node_modules", "action": "DELETE", "risk": "SAFE", "reason": "Regenerable using package-lock.json", "estimated_bytes": 1800000000},
                    {"path": "dist", "action": "DELETE", "risk": "SAFE", "reason": "Generated build output", "estimated_bytes": 420000000},
                    {"path": ".vite", "action": "DELETE", "risk": "SAFE", "reason": "Vite cache directory", "estimated_bytes": 86000000},
                ],
                "total_safe_recovery_bytes": 2306000000,
            })
        else:
            content = "Mock AI response for development. Configure NEBIUS_API_KEY for real AI."

        return AIResponse(content=content, model=self._model_name)

    async def structured_completion(
        self,
        messages: list[ChatMessage],
        response_schema: dict,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict:
        # Return mock structured data matching common schemas
        if "project_type" in str(response_schema):
            return {
                "project_type": "node",
                "framework": "react",
                "package_manager": "npm",
                "language": "typescript",
                "has_git": True,
                "cleanup_candidates": [
                    {"path": "node_modules", "risk": "SAFE", "reason": "Regenerable dependencies", "size_bytes": 1800000000},
                    {"path": "dist", "risk": "SAFE", "reason": "Build output", "size_bytes": 420000000},
                    {"path": ".vite", "risk": "SAFE", "reason": "Vite cache", "size_bytes": 86000000},
                ],
                "total_recoverable_bytes": 2306000000,
            }
        elif "plan" in str(response_schema):
            return {
                "plan": [
                    {"path": "node_modules", "action": "DELETE", "risk": "SAFE", "reason": "Regenerable using package-lock.json", "estimated_bytes": 1800000000},
                    {"path": "dist", "action": "DELETE", "risk": "SAFE", "reason": "Generated build output", "estimated_bytes": 420000000},
                    {"path": ".vite", "action": "DELETE", "risk": "SAFE", "reason": "Vite cache directory", "estimated_bytes": 86000000},
                ],
                "total_safe_recovery_bytes": 2306000000,
            }
        return {"result": "mock structured response"}


class RecordingTestProvider(AIProvider):
    """Test provider that records whether structured_completion was called and returns configurable results."""
    
    def __init__(self, model_name: str = "test-model", structured_response: Optional[dict] = None):
        self._model_name = model_name
        self._structured_response = structured_response or {}
        self.structured_completion_called = False
        self.last_messages: Optional[list[ChatMessage]] = None
        self.last_schema: Optional[dict] = None
    
    @property
    def provider_name(self) -> str:
        return "test"
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        return AIResponse(content="Test response", model=self._model_name)
    
    async def structured_completion(
        self,
        messages: list[ChatMessage],
        response_schema: dict,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> dict:
        self.structured_completion_called = True
        self.last_messages = messages
        self.last_schema = response_schema
        return self._structured_response