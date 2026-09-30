import os
from typing import Optional
from .provider import AIProvider, MockProvider
from .nebius_provider import NebiusProvider
from config import settings


def create_ai_provider() -> AIProvider:
    """Factory function to create the appropriate AI provider based on configuration."""
    if settings.DEVSWEEP_DEMO_MODE:
        return MockProvider(model_name="devsweep-demo")

    if settings.NEBIUS_API_KEY:
        try:
            return NebiusProvider(
                api_key=settings.NEBIUS_API_KEY,
                base_url=settings.NEBIUS_BASE_URL,
                model=settings.NEBIUS_MODEL,
            )
        except Exception as e:
            # Fall back to mock if Nebius fails to initialize
            print(f"Warning: Failed to initialize Nebius provider: {e}. Falling back to mock.")
            return MockProvider(model_name="nebius-fallback")

    # No API key and not in demo mode - use mock with warning
    print("Warning: NEBIUS_API_KEY not set. Using mock provider. Set NEBIUS_API_KEY for real AI features.")
    return MockProvider(model_name="devsweep-mock")


# Global provider instance (initialized on first use)
_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """Get the global AI provider instance, creating it if needed."""
    global _provider
    if _provider is None:
        _provider = create_ai_provider()
    return _provider


def reset_ai_provider() -> None:
    """Reset the global provider (useful for testing or config changes)."""
    global _provider
    _provider = None