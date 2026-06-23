"""test_agents.py — Tests for agent skills and AgentRunner."""
import pytest

from crawltop.agents.skills import SkillRegistry, SkillResult
from crawltop.agents.cleaner import CleanerSkill
from crawltop.agents.runner import AgentRunner
from crawltop.vector.embedder import chunk_text


# ---------------------------------------------------------------------------
# CleanerSkill tests (no LLM needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleaner_strips_boilerplate():
    skill = CleanerSkill()
    page = {
        "raw_text": "Breaking news article content here.\nSubscribe to our newsletter\nMore article content."
    }
    result = await skill.run(page, {})
    assert result.success
    assert result.clean_text is not None
    assert "Subscribe to our newsletter" not in result.clean_text
    assert "article content" in result.clean_text


@pytest.mark.asyncio
async def test_cleaner_returns_failure_on_empty():
    skill = CleanerSkill()
    result = await skill.run({}, {})
    assert not result.success
    assert result.error == "no text"


@pytest.mark.asyncio
async def test_cleaner_normalises_whitespace():
    skill = CleanerSkill()
    page = {"raw_text": "Line one.\n\n\n\n\nLine two."}
    result = await skill.run(page, {})
    assert result.success
    assert "\n\n\n" not in result.clean_text


# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------

def test_registry_has_builtin_skills():
    # Trigger registration by importing runner
    from crawltop.agents import runner  # noqa: F401
    skills = SkillRegistry.all()
    assert "cleaner" in skills
    assert "curator" in skills
    assert "linker" in skills
    assert "qa" in skills


def test_registry_build_returns_skill_instance():
    from crawltop.agents import runner  # noqa: F401
    skill = SkillRegistry.build("cleaner")
    assert skill is not None
    assert skill.name == "cleaner"


# ---------------------------------------------------------------------------
# AgentRunner tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_runner_runs_cleaner_without_llm():
    """Cleaner runs without LLM; curator/linker/qa skip gracefully."""
    runner = AgentRunner(settings={}, pipeline=["cleaner"])
    page = {"raw_text": "This is a real article. Subscribe to newsletter. More content here."}
    results = await runner.run_page(page)
    assert "cleaner" in results
    assert results["cleaner"].success


@pytest.mark.asyncio
async def test_runner_gracefully_skips_llm_skills_without_key():
    runner = AgentRunner(settings={}, pipeline=["cleaner", "curator", "linker", "qa"])
    page = {"raw_text": "Article about baseball players and teams. Aaron Judge hit a home run."}
    results = await runner.run_page(page)
    assert results["cleaner"].success
    # LLM skills should fail gracefully with error, not raise
    assert not results["curator"].success
    assert results["curator"].error is not None


# ---------------------------------------------------------------------------
# Embedder / chunker tests (no network needed)
# ---------------------------------------------------------------------------

def test_chunk_text_basic():
    text = " ".join(["word"] * 600)
    chunks = chunk_text(text, size=512, overlap=64)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.split()) <= 512


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_short():
    text = "hello world"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text
