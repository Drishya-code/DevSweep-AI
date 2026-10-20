from typing import Optional
from .provider import AIProvider
from .nebius_provider import NebiusProvider
from config import settings


def create_ai_provider() -> AIProvider:
    """Factory function to create the appropriate AI provider based on configuration."""
    if settings.NEBIUS_API_KEY:
        try:
            return NebiusProvider(
                api_key=settings.NEBIUS_API_KEY,
                base_url=settings.NEBIUS_BASE_URL,
                model=settings.NEBIUS_MODEL,
            )
        except Exception as e:
            # Keep initialization errors visible to callers; never disguise them as demo analysis.
            raise RuntimeError("Nebius provider configuration failed. Check the backend Nebius settings.") from e

    raise RuntimeError("Nebius configuration is missing: set NEBIUS_API_KEY on the backend.")


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
