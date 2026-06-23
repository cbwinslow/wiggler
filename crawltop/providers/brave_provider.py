"""brave_provider.py — Brave Web Search API provider."""
from __future__ import annotations

from typing import List

import httpx

from .base import SearchProvider, SearchResult


class BraveProvider(SearchProvider):
    """Search provider backed by the Brave Web Search API."""

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, num_results: int = 10) -> None:
        self.api_key = api_key
        self.num_results = num_results

    @property
    def name(self) -> str:
        return "brave"

    async def search(self, query: str) -> List[SearchResult]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": self.num_results,
            "text_decorations": False,
            "search_lang": "en",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self.BASE_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: List[SearchResult] = []
        web = data.get("web", {}).get("results", [])
        for item in web:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", "")[:300],
                    provider=self.name,
                    score=None,
                )
            )
        return results
