"""tests/test_entity_linker.py - unit tests for EntityLinker."""
import pytest
from crawltop.core.entity_linker import (
    EntityLinker,
    LinkedEntity,
    _normalise,
    _trigram_similarity,
)


class TestNormalise:
    def test_lowercase(self):
        assert _normalise("Yankees") == "yankees"

    def test_strips_punctuation(self):
        assert _normalise("Red Sox!") == "red sox"

    def test_collapses_whitespace(self):
        assert _normalise("New   York") == "new york"

    def test_empty(self):
        assert _normalise("") == ""


class TestTrigramSimilarity:
    def test_identical(self):
        assert _trigram_similarity("yankees", "yankees") == 1.0

    def test_empty(self):
        assert _trigram_similarity("", "yankees") == 0.0

    def test_partial(self):
        score = _trigram_similarity("yankee", "yankees")
        assert 0.5 < score < 1.0

    def test_unrelated(self):
        score = _trigram_similarity("yankees", "rockies")
        assert score < 0.5


class TestEntityLinkerTeam:
    def setup_method(self):
        self.linker = EntityLinker(db_path=None)

    def test_exact_team_name(self):
        result = self.linker.link_team("Yankees")
        assert result is not None
        assert result.canonical_id == "NYY"
        assert result.entity_type == "team"
        assert result.confidence > 0.8

    def test_city_name(self):
        result = self.linker.link_team("New York Yankees")
        assert result is not None
        assert result.canonical_id == "NYY"

    def test_dodgers(self):
        result = self.linker.link_team("Dodgers")
        assert result is not None
        assert result.canonical_id == "LAD"

    def test_red_sox(self):
        result = self.linker.link_team("Red Sox")
        assert result is not None
        assert result.canonical_id == "BOS"

    def test_cardinals(self):
        result = self.linker.link_team("Cardinals")
        assert result is not None
        assert result.canonical_id == "STL"

    def test_no_match(self):
        result = self.linker.link_team("xyzxyzxyz")
        assert result is None

    def test_linked_entity_fields(self):
        result = self.linker.link_team("Yankees")
        assert isinstance(result, LinkedEntity)
        assert result.raw == "Yankees"
        assert isinstance(result.canonical_name, str)
        assert 0 < result.confidence <= 1.0
        assert result.source == "local"

    def test_case_insensitive(self):
        r1 = self.linker.link_team("YANKEES")
        r2 = self.linker.link_team("yankees")
        assert r1 is not None and r2 is not None
        assert r1.canonical_id == r2.canonical_id

    def test_link_auto_team(self):
        result = self.linker.link("Yankees", hint="auto")
        assert result is not None
        assert result.canonical_id == "NYY"

    def test_link_player_without_db(self):
        """link_player returns None when no db_path given."""
        result = self.linker.link_player("Aaron Judge")
        assert result is None

    def test_all_30_teams_resolve(self):
        """Every team's first variant should resolve to its own abbreviation."""
        from crawltop.core.entity_linker import _MLB_TEAMS
        linker = EntityLinker(min_confidence=0.4)
        failures = []
        for abbrev, variants in _MLB_TEAMS.items():
            mention = variants[0].title()
            result = linker.link_team(mention)
            if result is None or result.canonical_id != abbrev:
                failures.append(
                    f"{abbrev}: '{mention}' -> {result.canonical_id if result else None}"
                )
        assert not failures, "Teams did not resolve correctly:\n" + "\n".join(failures)
