"""robots.py — robots.txt fetcher + TOS policy engine."""
from __future__ import annotations

import asyncio
import time
from enum import Enum
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

# ---------------------------------------------------------------------------
# Domains that explicitly prohibit automated scripts in their ToS.
# We hard-block these regardless of robots.txt.
# ---------------------------------------------------------------------------
_TOS_RESTRICTED: set[str] = {
    "mlb.com",
    "www.mlb.com",
    "m.mlb.com",
    "tickets.mlb.com",
}


class Policy(str, Enum):
    ALLOW = "allow"
    DISALLOW = "disallow"
    UNKNOWN = "unknown"


class RobotsCache:
    """Async cache of parsed RobotFileParser instances per domain."""

    TTL = 3600  # seconds

    def __init__(self) -> None:
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, domain: str, scheme: str = "https") -> RobotFileParser | None:
        async with self._lock:
            entry = self._cache.get(domain)
            if entry and (time.monotonic() - entry[1]) < self.TTL:
                return entry[0]
        robots_url = f"{scheme}://{domain}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(robots_url, follow_redirects=True)
                text = resp.text if resp.status_code == 200 else ""
        except Exception:
            text = ""
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        async with self._lock:
            self._cache[domain] = (parser, time.monotonic())
        return parser


class PolicyEngine:
    """Check crawl policy for a URL against robots.txt and ToS blocklist."""

    def __init__(self, user_agent: str = "wiggler-bot") -> None:
        self.user_agent = user_agent
        self._robots = RobotsCache()

    def _domain(self, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        return parsed.netloc, parsed.scheme

    def _is_tos_restricted(self, domain: str) -> bool:
        bare = domain.lstrip("www.") if domain.startswith("www.") else domain
        return domain in _TOS_RESTRICTED or bare in _TOS_RESTRICTED

    async def check(self, url: str) -> Policy:
        domain, scheme = self._domain(url)
        if self._is_tos_restricted(domain):
            return Policy.DISALLOW
        parser = await self._robots.get(domain, scheme)
        if parser is None:
            return Policy.UNKNOWN
        allowed = parser.can_fetch(self.user_agent, url)
        return Policy.ALLOW if allowed else Policy.DISALLOW

    async def crawl_delay(self, url: str) -> float:
        """Return the robots.txt Crawl-delay for this domain (default 1.0s)."""
        domain, scheme = self._domain(url)
        parser = await self._robots.get(domain, scheme)
        if parser is None:
            return 1.0
        delay = parser.crawl_delay(self.user_agent)
        return float(delay) if delay is not None else 1.0
