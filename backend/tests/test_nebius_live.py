"""Opt-in integration against the configured Nebius Token Factory account.

Set DEVSWEEP_RUN_NEBIUS_INTEGRATION=1 to make a real billable inference call.
"""
import os

import pytest

from ai.nebius_provider import NebiusProvider
from ai.provider import ChatMessage
from config import settings


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("DEVSWEEP_RUN_NEBIUS_INTEGRATION") != "1" or not settings.NEBIUS_API_KEY,
    reason="Set DEVSWEEP_RUN_NEBIUS_INTEGRATION=1 and NEBIUS_API_KEY to run live inference.",
)
async def test_nebius_token_factory_chat_completion():
    provider = NebiusProvider(settings.NEBIUS_API_KEY, settings.NEBIUS_BASE_URL, settings.NEBIUS_MODEL)
    response = await provider.chat_completion(
        [ChatMessage(role="user", content='Reply with exactly the word "ready".')],
        temperature=0,
        max_tokens=8,
    )
    assert response.content.strip()
    assert response.model
