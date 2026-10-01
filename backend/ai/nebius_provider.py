import os
import json
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from .provider import AIProvider, AIResponse, ChatMessage


class NebiusProvider(AIProvider):
    """Nebius Token Factory provider using OpenAI-compatible API with NVIDIA Nemotron models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "nvidia/nemotron-3-super-120b-a12b",
    ):
        self._api_key = api_key or os.getenv("NEBIUS_API_KEY")
        self._base_url = base_url or os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.us-central1.nebius.com/v1/")
        self._model = model or os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")

        if not self._api_key:
            raise ValueError("NEBIUS_API_KEY is required for NebiusProvider")

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    @property
    def provider_name(self) -> str:
        return "nebius"

    @property
    def model_name(self) -> str:
        return self._model

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Convert internal ChatMessage format to OpenAI format."""
        converted = []
        for msg in messages:
            openai_msg = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            converted.append(openai_msg)
        return converted

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Send a chat completion request to Nebius."""
        openai_messages = self._convert_messages(messages)

        kwargs = {
            "model": self._model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = await self._client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        return AIResponse(
            content=choice.message.content or "",
            usage=response.usage.model_dump() if response.usage else None,
            model=response.model,
        )

    async def structured_completion(
        self,
        messages: List[ChatMessage],
        response_schema: Dict[str, Any],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send a structured completion request with JSON schema validation."""
        # Add system message to enforce JSON schema
        system_msg = ChatMessage(
            role="system",
            content=f"You must respond with valid JSON matching this schema: {json.dumps(response_schema)}"
        )
        messages_with_schema = [system_msg] + messages

        openai_messages = self._convert_messages(messages_with_schema)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)