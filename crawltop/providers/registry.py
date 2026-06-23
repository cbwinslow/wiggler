"""registry.py — auto-build enabled search providers from settings."""
from __future__ import annotations

from typing import List

from .base import SearchProvider


def build_providers(settings) -> List[SearchProvider]:  # type: ignore[type-arg]
    """Return a list of enabled providers based on configured API keys."""
    from .exa_provider import ExaProvider
    from .brave_provider import BraveProvider

    providers: List[SearchProvider] = []

    exa_key = getattr(settings, "exa_api_key", None)
    if exa_key:
        providers.append(ExaProvider(api_key=exa_key))

    brave_key = getattr(settings, "brave_api_key", None)
    if brave_key:
        providers.append(BraveProvider(api_key=brave_key))

    return providers
