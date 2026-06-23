"""curator.py — CuratorSkill: LLM-powered summary, tags, and structured metadata."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .skills import Skill, SkillRegistry, SkillResult


_DEFAULT_PROMPT = """
You are a precise content curator. Given a webpage's extracted text, produce a JSON object with:
- "summary": a concise 2-4 sentence summary of the main content
- "tags": a list of 3-8 descriptive lowercase tags
- "title": the canonical article title (if identifiable)
- "publish_date": ISO date string if found, else null
- "author": author name if found, else null
- "confidence": float 0.0-1.0 for how confident you are in the extraction

Respond ONLY with valid JSON, no markdown fences.
"""


@SkillRegistry.register
class CuratorSkill(Skill):
    """
    LLM-powered curator. Requires an OpenAI-compatible API key.
    Falls back gracefully if no LLM is configured.
    """

    name = "curator"
    description = "Summarises content, extracts tags, title, author, publish date."
    version = "0.1.0"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_input_chars: int = 6000,
        prompt: Optional[str] = None,
    ) -> None:
        self.model = model
        self.max_input_chars = max_input_chars
        self.prompt = prompt or _DEFAULT_PROMPT

    async def run(self, page: dict, settings: dict) -> SkillResult:
        api_key = settings.get("openai_api_key") or settings.get("llm_api_key")
        if not api_key:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error="no LLM API key configured",
            )

        text = page.get("clean_text") or page.get("raw_text") or ""
        if not text:
            return SkillResult(skill_name=self.name, success=False, error="no text")

        truncated = text[: self.max_input_chars]
        try:
            result = await self._call_llm(truncated, api_key, settings)
            return SkillResult(
                skill_name=self.name,
                success=True,
                summary=result.get("summary"),
                tags=result.get("tags", []),
                confidence=float(result.get("confidence", 0.8)),
                raw_output=result,
            )
        except Exception as exc:
            return SkillResult(skill_name=self.name, success=False, error=str(exc))

    async def _call_llm(self, text: str, api_key: str, settings: dict) -> Dict[str, Any]:
        import httpx

        base_url = settings.get("llm_base_url", "https://api.openai.com/v1")
        model = settings.get("curator_model", self.model)
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": f"Webpage text:\n\n{text}"},
        ]
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": messages, "temperature": 0.2},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
