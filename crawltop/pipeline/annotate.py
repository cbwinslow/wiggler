"""annotate.py — Post-crawl annotation step: run AgentRunner + embed chunks into Qdrant."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional


async def annotate_page(
    page: dict,
    repo,
    agent_runner=None,
    embedder=None,
    qdrant_store=None,
    settings: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Full annotation pipeline for a single crawled page:
    1. Run AgentRunner skill pipeline (cleaner → curator → linker → qa).
    2. Persist skill results back to SQLite via repo.
    3. Chunk clean text and embed into Qdrant if embedder + store are provided.

    Returns the enriched page dict.
    """
    settings = settings or {}
    enriched = dict(page)

    # --- Step 1: Agent pipeline ---
    if agent_runner is not None:
        try:
            skill_results = await agent_runner.run_page(enriched)
            enriched["skill_results"] = {k: v.__dict__ for k, v in skill_results.items()}

            # Flatten top-level enrichment fields for DB storage
            cleaner_r = skill_results.get("cleaner")
            curator_r = skill_results.get("curator")
            linker_r = skill_results.get("linker")

            if cleaner_r and cleaner_r.success and cleaner_r.clean_text:
                enriched["clean_text"] = cleaner_r.clean_text
            if curator_r and curator_r.success:
                enriched["summary"] = curator_r.summary
                enriched["tags"] = curator_r.tags
            if linker_r and linker_r.success:
                enriched["entities"] = linker_r.entities
        except Exception as exc:
            enriched["agent_error"] = str(exc)

    # --- Step 2: Persist to SQLite ---
    if repo is not None:
        page_id = enriched.get("id")
        if page_id:
            try:
                await repo.update_page_annotations(
                    page_id=page_id,
                    clean_text=enriched.get("clean_text"),
                    summary=enriched.get("summary"),
                    tags=enriched.get("tags", []),
                    entities=enriched.get("entities", []),
                )
            except Exception:
                pass  # annotation failure should not block crawl

    # --- Step 3: Embed and index into Qdrant ---
    if embedder is not None and qdrant_store is not None:
        from crawltop.vector.embedder import chunk_text

        text = enriched.get("clean_text") or enriched.get("raw_text") or ""
        if text:
            chunks = chunk_text(text)
            try:
                vectors = await embedder.embed(chunks)
                for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                    await qdrant_store.upsert(
                        page_id=enriched.get("id", 0),
                        run_id=enriched.get("run_id", 0),
                        chunk=chunk,
                        vector=vector,
                        chunk_index=i,
                    )
                enriched["chunk_count"] = len(chunks)
            except Exception as exc:
                enriched["embed_error"] = str(exc)

    return enriched


async def annotate_run(
    run_id: int,
    repo,
    agent_runner=None,
    embedder=None,
    qdrant_store=None,
    settings: Optional[Dict[str, Any]] = None,
    concurrency: int = 4,
) -> List[dict]:
    """Annotate all pages for a completed run, concurrently."""
    pages = await repo.list_pages(run_id)
    sem = asyncio.Semaphore(concurrency)

    async def _annotate(page) -> dict:
        p = page.__dict__ if hasattr(page, "__dict__") else dict(page)
        async with sem:
            return await annotate_page(
                p,
                repo=repo,
                agent_runner=agent_runner,
                embedder=embedder,
                qdrant_store=qdrant_store,
                settings=settings,
            )

    return await asyncio.gather(*[_annotate(p) for p in pages])
