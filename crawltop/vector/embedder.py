"""embedder.py — Text chunker + embedding model abstraction."""
from __future__ import annotations

import asyncio
from typing import List, Optional


DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64


def chunk_text(text: str, size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks: List[str] = []
    step = max(1, size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + size])
        chunks.append(chunk)
        if i + size >= len(words):
            break
    return chunks


class Embedder:
    """
    Async embedding model wrapper.
    Supports OpenAI-compatible APIs and sentence-transformers (local).
    Set provider='openai' or provider='local' in settings.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self._local_model = None

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Return a list of embedding vectors for the given texts."""
        if self.provider == "local":
            return await self._embed_local(texts)
        return await self._embed_openai(texts)

    async def embed_one(self, text: str) -> List[float]:
        results = await self.embed([text])
        return results[0]

    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": texts}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        return [item["embedding"] for item in data["data"]]

    async def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Use sentence-transformers in a thread pool to avoid blocking."""
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._local_model = SentenceTransformer(self.model)

        loop = asyncio.get_event_loop()
        model = self._local_model

        def _run() -> List[List[float]]:
            return model.encode(texts, show_progress_bar=False).tolist()

        return await loop.run_in_executor(None, _run)
