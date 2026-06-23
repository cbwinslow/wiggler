"""exa_provider.py — Exa neural search provider."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import httpx

from .base import SearchProvider, SearchResult


class ExaProvider(SearchProvider):
    """Search provider backed by the Exa neural search API."""

    BASE_URL = "https://api.exa.ai/search"

    def __init__(self, api_key: str, num_results: int = 10) -> None:
        self.api_key = api_key
        self.num_results = num_results

    @property
    def name(self) -> str:
        return "exa"

    async def search(self, query: str) -> List[SearchResult]:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "numResults": self.num_results,
            "type": "neural",
            "useAutoprompt": True,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(self.BASE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results: List[SearchResult] = []
        for item in data.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("text", "")[:300],
                    provider=self.name,
                    score=item.get("score"),
                )
            )
        return results
