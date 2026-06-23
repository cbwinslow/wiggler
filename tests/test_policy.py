"""test_policy.py — Tests for the PolicyEngine."""
import pytest
from crawltop.core.robots import Policy, PolicyEngine


@pytest.mark.asyncio
async def test_tos_blocked_domain():
    engine = PolicyEngine()
    result = await engine.check("https://www.mlb.com/news/some-article")
    assert result == Policy.DISALLOW


@pytest.mark.asyncio
async def test_tos_blocked_subdomain():
    engine = PolicyEngine()
    result = await engine.check("https://mlb.com/")
    assert result == Policy.DISALLOW


@pytest.mark.asyncio
async def test_allowed_domain_returns_policy():
    """Non-TOS-blocked domains should return ALLOW or DISALLOW (not error)."""
    engine = PolicyEngine()
    result = await engine.check("https://example.com/")
    assert result in (Policy.ALLOW, Policy.DISALLOW, Policy.UNKNOWN)


@pytest.mark.asyncio
async def test_crawl_delay_default():
    engine = PolicyEngine()
    # mlb.com is TOS blocked, but crawl_delay should still return a float
    delay = await engine.crawl_delay("https://example.com/")
    assert isinstance(delay, float)
    assert delay >= 0
