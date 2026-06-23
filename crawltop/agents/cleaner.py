"""cleaner.py — CleanerSkill: removes boilerplate, normalises whitespace, strips ads."""
from __future__ import annotations

import re
from typing import Optional

from .skills import Skill, SkillRegistry, SkillResult


_BOILERPLATE_PATTERNS = [
    r"(?i)subscribe to (our )?newsletter",
    r"(?i)cookies? (policy|consent|notice|settings)",
    r"(?i)advertisement",
    r"(?i)follow us on (twitter|facebook|instagram|tiktok)",
    r"(?i)\bshare (this )?article\b",
    r"(?i)all rights reserved",
    r"(?i)\bcopyright \d{4}\b",
    r"(?i)privacy policy",
    r"(?i)terms (of (use|service))?",
]

_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS))


@SkillRegistry.register
class CleanerSkill(Skill):
    """
    Deterministic text cleaner.
    No LLM required — runs on every page regardless of AI settings.
    """

    name = "cleaner"
    description = "Strips boilerplate, normalises whitespace, removes ad copy."
    version = "0.1.0"

    async def run(self, page: dict, settings: dict) -> SkillResult:
        raw = page.get("clean_text") or page.get("raw_text") or ""
        if not raw:
            return SkillResult(skill_name=self.name, success=False, error="no text")

        cleaned = self._clean(raw)
        return SkillResult(
            skill_name=self.name,
            success=True,
            clean_text=cleaned,
            confidence=1.0,
        )

    def _clean(self, text: str) -> str:
        # Split into lines, drop boilerplate lines
        lines = text.splitlines()
        kept = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if len(stripped) < 20 and stripped.endswith((".", "!", "?")) is False:
                # very short lines are usually nav/UI remnants
                if len(stripped) < 8:
                    continue
            if _BOILERPLATE_RE.search(stripped):
                continue
            kept.append(stripped)

        # Normalise whitespace
        cleaned = "\n".join(kept)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
