"""linker.py — LinkerSkill: extracts named entities and links them to known records."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from .skills import Skill, SkillRegistry, SkillResult


_LINKER_PROMPT = """
You are a named entity extractor for sports and news content.
Given a webpage's text, extract all named entities and categorize them.

Return a JSON object:
- "entities": list of objects, each with:
  - "name": the entity name as it appears
  - "type": one of [PERSON, TEAM, LEAGUE, STADIUM, ORGANIZATION, LOCATION, EVENT, OTHER]
  - "context": a short phrase showing how it was used (max 80 chars)

Focus on proper nouns. Include athletes, coaches, teams, leagues, venues.
Respond ONLY with valid JSON.
"""


@SkillRegistry.register
class LinkerSkill(Skill):
    """
    LLM-powered entity extractor and linker.
    Extracts PERSON, TEAM, LEAGUE, etc. from page text.
    Future: links to canonical entity IDs in the wiggler entity graph.
    """

    name = "linker"
    description = "Extracts named entities (players, teams, orgs) from page text."
    version = "0.1.0"

    def __init__(self, model: str = "gpt-4o-mini", max_input_chars: int = 5000) -> None:
        self.model = model
        self.max_input_chars = max_input_chars

    async def run(self, page: dict, settings: dict) -> SkillResult:
        api_key = settings.get("openai_api_key") or settings.get("llm_api_key")
        if not api_key:
            return SkillResult(skill_name=self.name, success=False, error="no LLM API key")

        text = (page.get("clean_text") or page.get("raw_text") or "")[: self.max_input_chars]
        if not text:
            return SkillResult(skill_name=self.name, success=False, error="no text")

        try:
            result = await self._call_llm(text, api_key, settings)
            entities = result.get("entities", [])
            return SkillResult(
                skill_name=self.name,
                success=True,
                entities=entities,
                confidence=0.85,
                raw_output=result,
            )
        except Exception as exc:
            return SkillResult(skill_name=self.name, success=False, error=str(exc))

    async def _call_llm(self, text: str, api_key: str, settings: dict) -> Dict[str, Any]:
        import httpx

        base_url = settings.get("llm_base_url", "https://api.openai.com/v1")
        model = settings.get("linker_model", self.model)
        messages = [
            {"role": "system", "content": _LINKER_PROMPT},
            {"role": "user", "content": text},
        ]
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.1},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
