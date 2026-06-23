"""qdrant_store.py — Qdrant local-mode vector store for Wiggler."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional


COLLECTION_NAME = "wiggler_pages"
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small default; override for local models


class QdrantStore:
    """
    Thin async wrapper around qdrant-client in local/in-process mode.
    Uses on-disk persistence when path is provided, otherwise in-memory.

    Usage:
        store = QdrantStore(path=".wiggler_qdrant")
        await store.init(vector_size=1536)
        await store.upsert(page_id=42, run_id=1, chunk="...", vector=[...])
        results = await store.search(query_vector=[...], top_k=5)
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path  # None = in-memory
        self._client = None

    def _get_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient  # type: ignore
            if self.path:
                self._client = QdrantClient(path=self.path)
            else:
                self._client = QdrantClient(":memory:")
        return self._client

    async def init(self, vector_size: int = VECTOR_SIZE, force_recreate: bool = False) -> None:
        """Create collection if it doesn't exist."""
        import asyncio
        from qdrant_client.models import Distance, VectorParams  # type: ignore

        client = self._get_client()
        loop = asyncio.get_event_loop()

        def _create():
            existing = [c.name for c in client.get_collections().collections]
            if COLLECTION_NAME in existing and not force_recreate:
                return
            if COLLECTION_NAME in existing:
                client.delete_collection(COLLECTION_NAME)
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

        await loop.run_in_executor(None, _create)

    async def upsert(
        self,
        page_id: int,
        run_id: int,
        chunk: str,
        vector: List[float],
        chunk_index: int = 0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Insert or update a chunk vector. Returns the point ID."""
        import asyncio
        from qdrant_client.models import PointStruct  # type: ignore

        point_id = str(uuid.uuid4())
        payload = {
            "page_id": page_id,
            "run_id": run_id,
            "chunk_index": chunk_index,
            "chunk": chunk[:1000],  # keep payload lean
            **(extra or {}),
        }
        client = self._get_client()
        loop = asyncio.get_event_loop()

        def _upsert():
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=point_id, vector=vector, payload=payload)],
            )

        await loop.run_in_executor(None, _upsert)
        return point_id

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        run_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return top-k similar chunks, optionally filtered by run_id."""
        import asyncio
        from qdrant_client.models import Filter, FieldCondition, MatchValue  # type: ignore

        client = self._get_client()
        loop = asyncio.get_event_loop()
        query_filter = None
        if run_id is not None:
            query_filter = Filter(
                must=[FieldCondition(key="run_id", match=MatchValue(value=run_id))]
            )

        def _search():
            return client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )

        hits = await loop.run_in_executor(None, _search)
        return [
            {
                "score": h.score,
                "page_id": h.payload.get("page_id"),
                "run_id": h.payload.get("run_id"),
                "chunk": h.payload.get("chunk"),
                "chunk_index": h.payload.get("chunk_index"),
            }
            for h in hits
        ]

    async def count(self) -> int:
        """Return total number of vectors stored."""
        import asyncio
        client = self._get_client()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: client.count(collection_name=COLLECTION_NAME)
        )
        return result.count
