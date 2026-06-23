"""skills.py — Open skill interface for Wiggler agents.

Skills are the atomic units of agent capability. Each skill:
- Accepts a PageRecord dict as input.
- Returns an SkillResult with enriched fields.
- Is configurable via settings (prompt, model, temperature, enabled).
- Can be contributed by the community (open-source plugin pattern).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillResult:
    """Output from a single skill execution."""
    skill_name: str
    success: bool
    # Core enrichment fields
    clean_text: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    entities: List[Dict[str, str]] = field(default_factory=list)  # [{name, type, context}]
    confidence: float = 1.0
    notes: Optional[str] = None
    raw_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Skill(ABC):
    """
    Base class for all Wiggler agent skills.

    To create a custom skill:
        class MySkill(Skill):
            name = "my_skill"
            description = "Does something useful."

            async def run(self, page: dict, settings: dict) -> SkillResult:
                ...
    """

    name: str = "base"
    description: str = ""
    version: str = "0.1.0"
    author: str = "wiggler"

    @abstractmethod
    async def run(self, page: dict, settings: dict) -> SkillResult:
        """Execute this skill on a page record. Must be overridden."""
        ...

    def __repr__(self) -> str:
        return f"<Skill:{self.name} v{self.version}>"


class SkillRegistry:
    """Global registry of available skills. Skills register themselves on import."""

    _skills: Dict[str, type] = {}

    @classmethod
    def register(cls, skill_cls: type) -> type:
        """Register a skill class. Use as a decorator: @SkillRegistry.register."""
        cls._skills[skill_cls.name] = skill_cls
        return skill_cls

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        return cls._skills.get(name)

    @classmethod
    def all(cls) -> Dict[str, type]:
        return dict(cls._skills)

    @classmethod
    def build(cls, name: str, **kwargs) -> Optional["Skill"]:
        """Instantiate a skill by name."""
        skill_cls = cls._skills.get(name)
        if skill_cls is None:
            return None
        return skill_cls(**kwargs)
