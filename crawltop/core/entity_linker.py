"""crawltop/core/entity_linker.py

MLB entity linking: resolve raw strings (team names, player names, game IDs)
to canonical identifiers stored in the local SQLite DB.

Design goals
------------
* Zero external network calls - everything is resolved from local DB / seed data.
* Fast fuzzy matching via a simple trigram similarity score (no heavy deps).
* Pluggable: subclass EntityLinker and override `_candidates` to use an
  external knowledge graph or vector store.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Canonical MLB teams seed (abbrev -> full name variants)
# ---------------------------------------------------------------------------
_MLB_TEAMS: dict[str, list[str]] = {
    "ARI": ["arizona", "diamondbacks", "d-backs"],
    "ATL": ["atlanta", "braves"],
    "BAL": ["baltimore", "orioles", "o's"],
    "BOS": ["boston", "red sox"],
    "CHC": ["chicago cubs", "cubs"],
    "CWS": ["chicago white sox", "white sox"],
    "CIN": ["cincinnati", "reds"],
    "CLE": ["cleveland", "guardians"],
    "COL": ["colorado", "rockies"],
    "DET": ["detroit", "tigers"],
    "HOU": ["houston", "astros"],
    "KC":  ["kansas city", "royals"],
    "LAA": ["los angeles angels", "angels", "anaheim"],
    "LAD": ["los angeles dodgers", "dodgers", "la dodgers"],
    "MIA": ["miami", "marlins"],
    "MIL": ["milwaukee", "brewers"],
    "MIN": ["minnesota", "twins"],
    "NYM": ["new york mets", "mets"],
    "NYY": ["new york yankees", "yankees"],
    "OAK": ["oakland", "athletics", "a's"],
    "PHI": ["philadelphia", "phillies"],
    "PIT": ["pittsburgh", "pirates"],
    "SD":  ["san diego", "padres"],
    "SEA": ["seattle", "mariners"],
    "SF":  ["san francisco", "giants", "sf giants"],
    "STL": ["st. louis", "st louis", "cardinals"],
    "TB":  ["tampa bay", "rays"],
    "TEX": ["texas", "rangers"],
    "TOR": ["toronto", "blue jays"],
    "WSH": ["washington", "nationals", "nats"],
}


@dataclass
class LinkedEntity:
    """Result of entity linking for a single mention."""

    raw: str
    entity_type: str          # "team" | "player" | "game"
    canonical_id: str         # e.g. "NYY" or player_id string
    canonical_name: str
    confidence: float         # 0.0 - 1.0
    source: str = "local"     # "local" | "db" | "vector"
    meta: dict = field(default_factory=dict)


class EntityLinker:
    """Resolve raw entity mentions to canonical MLB identifiers.

    Parameters
    ----------
    db_path:
        Path to the crawltop SQLite database.  If *None* only the built-in
        seed data is used (useful for tests).
    min_confidence:
        Minimum trigram similarity score (0-1) to accept a match.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        min_confidence: float = 0.55,
    ) -> None:
        self.db_path = db_path
        self.min_confidence = min_confidence
        self._team_index = self._build_team_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def link_team(self, mention: str) -> Optional[LinkedEntity]:
        """Attempt to resolve *mention* to a canonical MLB team."""
        norm = _normalise(mention)
        best_id, best_score = None, 0.0
        for abbrev, variants in self._team_index.items():
            for v in variants:
                score = _trigram_similarity(norm, v)
                if score > best_score:
                    best_score = score
                    best_id = abbrev
        if best_id is None or best_score < self.min_confidence:
            return None
        return LinkedEntity(
            raw=mention,
            entity_type="team",
            canonical_id=best_id,
            canonical_name=self._canonical_name(best_id),
            confidence=round(best_score, 4),
        )

    def link_player(self, mention: str) -> Optional[LinkedEntity]:
        """Resolve a player name via the local DB `players` table."""
        if self.db_path is None:
            return None
        norm = _normalise(mention)
        candidates = self._db_player_candidates(norm)
        best: Optional[tuple[str, str, float]] = None
        for pid, name in candidates:
            score = _trigram_similarity(norm, _normalise(name))
            if best is None or score > best[2]:
                best = (pid, name, score)
        if best is None or best[2] < self.min_confidence:
            return None
        return LinkedEntity(
            raw=mention,
            entity_type="player",
            canonical_id=best[0],
            canonical_name=best[1],
            confidence=round(best[2], 4),
            source="db",
        )

    def link(self, mention: str, hint: str = "auto") -> Optional[LinkedEntity]:
        """Auto-detect entity type and link.

        hint: "team" | "player" | "auto"
        """
        if hint == "team":
            return self.link_team(mention)
        if hint == "player":
            return self.link_player(mention)
        # Auto: try team first, then player
        result = self.link_team(mention)
        if result and result.confidence >= self.min_confidence:
            return result
        return self.link_player(mention)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _build_team_index() -> dict[str, list[str]]:
        return {k: [_normalise(v) for v in variants]
                for k, variants in _MLB_TEAMS.items()}

    @staticmethod
    def _canonical_name(abbrev: str) -> str:
        """Return a display name for a team abbreviation."""
        variants = _MLB_TEAMS.get(abbrev, [abbrev])
        # Return the first (most descriptive) variant, title-cased
        return variants[0].title() if variants else abbrev

    def _db_player_candidates(
        self, norm_mention: str
    ) -> list[tuple[str, str]]:
        """Return (player_id, full_name) pairs from the DB.

        Uses a simple LIKE prefix to limit candidates before scoring.
        """
        if self.db_path is None:
            return []
        try:
            con = sqlite3.connect(self.db_path)
            prefix = norm_mention[:4] if len(norm_mention) >= 4 else norm_mention
            rows = con.execute(
                "SELECT player_id, full_name FROM players "
                "WHERE lower(full_name) LIKE ?",
                (f"%{prefix}%",),
            ).fetchall()
            con.close()
            return [(str(r[0]), str(r[1])) for r in rows]
        except Exception:  # noqa: BLE001
            return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _trigrams(s: str) -> set[str]:
    """Return the set of character trigrams for *s* (padded)."""
    padded = f"  {s} "
    return {padded[i: i + 3] for i in range(len(padded) - 2)}


def _trigram_similarity(a: str, b: str) -> float:
    """Dice coefficient over character trigrams."""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return 2 * len(ta & tb) / (len(ta) + len(tb))
