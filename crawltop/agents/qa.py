"""qa.py — QASkill: validates curated output against the source text."""
from __future__ import annotations

import json
from typing import Any, Dict

from .skills import Skill, SkillRegistry, SkillResult


_QA_PROMPT = """
You are a quality assurance reviewer for extracted web content.
Given the original source text and a curator's JSON summary, evaluate:
1. Is the summary factually consistent with the source? (no hallucinations)
2. Are the tags relevant and accurate?
3. Is the title correct?

Return a JSON object:
- "pass": true/false
- "confidence": float 0.0-1.0
- "issues": list of strings describing any problems found (empty if pass)

Respond ONLY with valid JSON.
"""


@SkillRegistry.register
class QASkill(Skill):
    """
    LLM-powered QA validator.
    Checks curator output against the source text for faithfulness.
    Skipped gracefully if no LLM is configured.
    """

    name = "qa"
    description = "Validates curator output against source text for faithfulness."
    version = "0.1.0"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    async def run(self, page: dict, settings: dict) -> SkillResult:
        api_key = settings.get("openai_api_key") or settings.get("llm_api_key")
        if not api_key:
            return SkillResult(skill_name=self.name, success=False, error="no LLM API key")

        source = (page.get("clean_text") or page.get("raw_text") or "")[:4000]
        curator_output = page.get("curator_output") or {}
        if not source or not curator_output:
            return SkillResult(skill_name=self.name, success=False, error="missing inputs")

        try:
            result = await self._call_llm(source, curator_output, api_key, settings)
            passed = result.get("pass", False)
            issues = result.get("issues", [])
            return SkillResult(
                skill_name=self.name,
                success=True,
                confidence=float(result.get("confidence", 0.5)),
                notes="PASS" if passed else f"FAIL: {'; '.join(issues)}",
                raw_output=result,
            )
        except Exception as exc:
            return SkillResult(skill_name=self.name, success=False, error=str(exc))

    async def _call_llm(self, source: str, curator_out: dict, api_key: str, settings: dict) -> Dict[str, Any]:
        import httpx

        base_url = settings.get("llm_base_url", "https://api.openai.com/v1")
        model = settings.get("qa_model", self.model)
        user_msg = f"Source text (truncated):\n{source}\n\nCurator output:\n{json.dumps(curator_out, indent=2)}"
        messages = [
            {"role": "system", "content": _QA_PROMPT},
            {"role": "user", "content": user_msg},
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
