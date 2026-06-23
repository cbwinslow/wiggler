"""policy_config.py — Per-domain crawl policy configuration.

Allows defining depth, rate, allowed paths, TOS status, and pipeline config
per domain. Loaded from a YAML/JSON config file or programmatically.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DomainPolicy:
    """Crawl policy for a single domain."""
    domain: str
    enabled: bool = True
    tos_restricted: bool = False
    respect_robots: bool = True
    max_depth: int = 3
    max_pages: int = 100
    crawl_delay: float = 2.0          # seconds between requests
    allowed_paths: List[str] = field(default_factory=list)   # empty = all
    blocked_paths: List[str] = field(default_factory=list)
    allowed_mime_types: List[str] = field(default_factory=lambda: ["text/html"])
    pipeline: List[str] = field(default_factory=lambda: ["cleaner", "curator", "linker", "qa"])
    embed: bool = True
    notes: str = ""

    def allows_path(self, path: str) -> bool:
        """Return True if this path is allowed under policy."""
        if self.tos_restricted:
            return False
        for blocked in self.blocked_paths:
            if path.startswith(blocked):
                return False
        if self.allowed_paths:
            return any(path.startswith(p) for p in self.allowed_paths)
        return True


class PolicyConfig:
    """
    Registry of per-domain crawl policies.
    Loaded from a JSON config file; falls back to sensible defaults.

    Config file format (wiggler_policies.json):
    {
      "domains": [
        {
          "domain": "example.com",
          "max_depth": 2,
          "crawl_delay": 1.5,
          "pipeline": ["cleaner", "curator"]
        }
      ]
    }
    """

    # Hard-coded TOS-restricted domains (always blocked)
    _TOS_BLOCKED: set = {
        "mlb.com", "www.mlb.com", "m.mlb.com", "tickets.mlb.com",
    }

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._policies: Dict[str, DomainPolicy] = {}
        self._load_tos_blocked()
        if config_path and config_path.exists():
            self._load_file(config_path)

    def _load_tos_blocked(self) -> None:
        for domain in self._TOS_BLOCKED:
            self._policies[domain] = DomainPolicy(
                domain=domain,
                enabled=False,
                tos_restricted=True,
                notes="Hard-blocked: ToS prohibits automated scripts.",
            )

    def _load_file(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("domains", []):
            domain = entry.pop("domain")
            policy = DomainPolicy(domain=domain, **entry)
            self._policies[domain] = policy

    def get(self, domain: str) -> DomainPolicy:
        """Return policy for domain, or a safe permissive default."""
        return self._policies.get(domain, DomainPolicy(domain=domain))

    def register(self, policy: DomainPolicy) -> None:
        """Programmatically register or override a domain policy."""
        self._policies[policy.domain] = policy

    def is_allowed(self, domain: str) -> bool:
        p = self.get(domain)
        return p.enabled and not p.tos_restricted

    def all_domains(self) -> List[str]:
        return sorted(self._policies.keys())

    def to_json(self) -> str:
        return json.dumps(
            {"domains": [asdict(p) for p in self._policies.values()]},
            indent=2,
        )


# Module-level singleton
_default_config: Optional[PolicyConfig] = None


def get_policy_config(config_path: Optional[Path] = None) -> PolicyConfig:
    """Return the module-level PolicyConfig singleton."""
    global _default_config
    if _default_config is None:
        _default_config = PolicyConfig(config_path)
    return _default_config
