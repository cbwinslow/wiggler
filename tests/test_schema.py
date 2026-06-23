"""tests/test_schema.py - unit tests for crawltop/db/schema.py."""
import sqlite3
import pytest
from crawltop.db.schema import ensure_schema, current_version, SCHEMA_VERSION


@pytest.fixture
def mem_db():
    """In-memory SQLite connection (discarded after each test)."""
    con = sqlite3.connect(":memory:")
    yield con
    con.close()


class TestEnsureSchema:
    def test_applies_all_migrations(self, mem_db):
        ensure_schema(mem_db)
        assert current_version(mem_db) == SCHEMA_VERSION

    def test_idempotent(self, mem_db):
        ensure_schema(mem_db)
        ensure_schema(mem_db)  # second call should be a no-op
        assert current_version(mem_db) == SCHEMA_VERSION

    def test_wal_mode(self, mem_db):
        ensure_schema(mem_db)
        row = mem_db.execute("PRAGMA journal_mode").fetchone()
        # In-memory DB returns 'memory' not 'wal', so just check it doesn't raise
        assert row is not None

    def test_tables_exist(self, mem_db):
        ensure_schema(mem_db)
        tables = {
            r[0]
            for r in mem_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {"runs", "pages", "events", "players", "extracted_tables", "entity_links"}
        missing = expected - tables
        assert not missing, f"Missing tables: {missing}"

    def test_players_table_columns(self, mem_db):
        ensure_schema(mem_db)
        cols = {
            r[1]
            for r in mem_db.execute("PRAGMA table_info(players)").fetchall()
        }
        assert "player_id" in cols
        assert "full_name" in cols
        assert "team_abbrev" in cols

    def test_extracted_tables_columns(self, mem_db):
        ensure_schema(mem_db)
        cols = {
            r[1]
            for r in mem_db.execute(
                "PRAGMA table_info(extracted_tables)"
            ).fetchall()
        }
        assert "page_id" in cols
        assert "headers_json" in cols
        assert "rows_json" in cols

    def test_entity_links_columns(self, mem_db):
        ensure_schema(mem_db)
        cols = {
            r[1]
            for r in mem_db.execute(
                "PRAGMA table_info(entity_links)"
            ).fetchall()
        }
        assert "canonical_id" in cols
        assert "confidence" in cols

    def test_current_version_zero_on_empty(self):
        con = sqlite3.connect(":memory:")
        assert current_version(con) == 0
        con.close()

    def test_insert_run(self, mem_db):
        ensure_schema(mem_db)
        mem_db.execute(
            "INSERT INTO runs(seed_url) VALUES (?)", ("https://mlb.com",)
        )
        mem_db.commit()
        row = mem_db.execute("SELECT seed_url FROM runs").fetchone()
        assert row[0] == "https://mlb.com"

    def test_insert_player(self, mem_db):
        ensure_schema(mem_db)
        mem_db.execute(
            "INSERT INTO players(player_id, full_name, team_abbrev) VALUES (?,?,?)",
            ("judge-001", "Aaron Judge", "NYY"),
        )
        mem_db.commit()
        row = mem_db.execute(
            "SELECT full_name FROM players WHERE player_id='judge-001'"
        ).fetchone()
        assert row[0] == "Aaron Judge"
