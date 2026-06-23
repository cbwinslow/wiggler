"""runner.py — AgentRunner: orchestrates the skill pipeline for a single page."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .skills import SkillRegistry, SkillResult

# Auto-register built-in skills on import
from . import cleaner  # noqa: F401
from . import curator  # noqa: F401
from . import qa       # noqa: F401
from . import linker   # noqa: F401


# Default pipeline order
DEFAULT_PIPELINE: List[str] = ["cleaner", "curator", "linker", "qa"]


class AgentRunner:
    """
    Runs a configurable skill pipeline on a page dict.

    Each skill receives the page dict (which is mutated with results after each step)
    and the settings dict. Skills run sequentially; the cleaner always runs first.

    Usage:
        runner = AgentRunner(settings={"openai_api_key": "..."})
        results = await runner.run_page(page_dict)
    """

    def __init__(
        self,
        settings: Optional[Dict[str, Any]] = None,
        pipeline: Optional[List[str]] = None,
    ) -> None:
        self.settings = settings or {}
        self.pipeline = pipeline or DEFAULT_PIPELINE

    async def run_page(self, page: dict) -> Dict[str, SkillResult]:
        """
        Run the configured skill pipeline on a single page.
        Returns a dict of {skill_name: SkillResult}.
        """
        results: Dict[str, SkillResult] = {}
        page = dict(page)  # shallow copy; don't mutate caller's dict

        for skill_name in self.pipeline:
            skill_cls = SkillRegistry.get(skill_name)
            if skill_cls is None:
                continue
            skill = skill_cls() if skill_name not in ("curator", "linker", "qa") else skill_cls()
            try:
                result = await skill.run(page, self.settings)
            except Exception as exc:
                result = SkillResult(skill_name=skill_name, success=False, error=str(exc))

            results[skill_name] = result

            # Propagate enrichment forward in the pipeline
            if result.success:
                if result.clean_text:
                    page["clean_text"] = result.clean_text
                if result.summary:
                    page["summary"] = result.summary
                if result.tags:
                    page.setdefault("tags", []).extend(result.tags)
                if result.entities:
                    page.setdefault("entities", []).extend(result.entities)
                if result.raw_output and skill_name == "curator":
                    page["curator_output"] = result.raw_output

        return results

    async def run_pages_batch(
        self,
        pages: List[dict],
        concurrency: int = 4,
    ) -> List[Dict[str, SkillResult]]:
        """Run the pipeline on multiple pages concurrently."""
        sem = asyncio.Semaphore(concurrency)

        async def _run(page: dict) -> Dict[str, SkillResult]:
            async with sem:
                return await self.run_page(page)

        return await asyncio.gather(*[_run(p) for p in pages])
