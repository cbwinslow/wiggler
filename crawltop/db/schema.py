"""crawltop/db/schema.py

Schema versioning and migration manager for the crawltop SQLite database.

Version history
---------------
v1  baseline tables: runs, pages, events
v2  add: players, extracted_tables, entity_links, full-text-search triggers

Usage
-----
    from crawltop.db.schema import ensure_schema
    con = sqlite3.connect("crawltop.db")
    ensure_schema(con)          # idempotent - safe to call every startup
"""
from __future__ import annotations

import sqlite3
import logging

log = logging.getLogger(__name__)

SCHEMA_VERSION = 2

# ---------------------------------------------------------------------------
# DDL - each migration is a list of SQL statements
# ---------------------------------------------------------------------------
_MIGRATIONS: dict[int, list[str]] = {
    1: [
        # Baseline tables (created on first run if not present)
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            finished_at TEXT,
            seed_url    TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'running',
            pages_crawled INTEGER NOT NULL DEFAULT 0,
            config_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS pages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            url         TEXT    NOT NULL,
            fetched_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            status_code INTEGER,
            content_type TEXT,
            html        TEXT,
            text        TEXT,
            title       TEXT,
            depth       INTEGER NOT NULL DEFAULT 0,
            embedding_id TEXT
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_pages_run_id ON pages(run_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url);
        """,
        """
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER REFERENCES runs(id) ON DELETE CASCADE,
            page_id     INTEGER REFERENCES pages(id) ON DELETE CASCADE,
            ts          TEXT    NOT NULL DEFAULT (datetime('now')),
            level       TEXT    NOT NULL DEFAULT 'INFO',
            message     TEXT    NOT NULL
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);
        """,
    ],
    2: [
        # v2 - MLB-focused additions
        """
        CREATE TABLE IF NOT EXISTS players (
            player_id   TEXT PRIMARY KEY,
            full_name   TEXT NOT NULL,
            team_abbrev TEXT,
            position    TEXT,
            bats        TEXT,
            throws      TEXT,
            birth_date  TEXT,
            meta_json   TEXT,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_players_name
            ON players(lower(full_name));
        """,
        """
        CREATE TABLE IF NOT EXISTS extracted_tables (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id     INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
            table_index INTEGER NOT NULL DEFAULT 0,
            caption     TEXT,
            headers_json TEXT NOT NULL,
            rows_json   TEXT NOT NULL,
            row_count   INTEGER NOT NULL DEFAULT 0,
            extracted_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ext_tables_page
            ON extracted_tables(page_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS entity_links (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id         INTEGER REFERENCES pages(id) ON DELETE CASCADE,
            extracted_table_id INTEGER REFERENCES extracted_tables(id)
                                ON DELETE CASCADE,
            raw_mention     TEXT NOT NULL,
            entity_type     TEXT NOT NULL,
            canonical_id    TEXT NOT NULL,
            canonical_name  TEXT NOT NULL,
            confidence      REAL NOT NULL,
            source          TEXT NOT NULL DEFAULT 'local',
            linked_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_entity_links_canonical
            ON entity_links(entity_type, canonical_id);
        """,
        # FTS virtual table over pages.text for fast keyword search
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts
            USING fts5(title, text, content=pages, content_rowid=id);
        """,
        # Triggers to keep FTS in sync
        """
        CREATE TRIGGER IF NOT EXISTS pages_fts_insert
        AFTER INSERT ON pages BEGIN
            INSERT INTO pages_fts(rowid, title, text)
            VALUES (new.id, new.title, new.text);
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS pages_fts_update
        AFTER UPDATE ON pages BEGIN
            INSERT INTO pages_fts(pages_fts, rowid, title, text)
            VALUES ('delete', old.id, old.title, old.text);
            INSERT INTO pages_fts(rowid, title, text)
            VALUES (new.id, new.title, new.text);
        END;
        """,
        """
        CREATE TRIGGER IF NOT EXISTS pages_fts_delete
        AFTER DELETE ON pages BEGIN
            INSERT INTO pages_fts(pages_fts, rowid, title, text)
            VALUES ('delete', old.id, old.title, old.text);
        END;
        """,
    ],
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def ensure_schema(con: sqlite3.Connection) -> None:
    """Apply any pending migrations to *con* and enable WAL mode.

    Safe to call on every application startup - migrations are idempotent.
    """
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")

    # Ensure the version tracking table exists first
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
    )
    con.commit()

    current = _current_version(con)
    log.debug("DB schema version: %d (target: %d)", current, SCHEMA_VERSION)

    for ver in sorted(_MIGRATIONS):
        if ver <= current:
            continue
        log.info("Applying schema migration v%d", ver)
        with con:
            for stmt in _MIGRATIONS[ver]:
                con.execute(stmt)
            con.execute(
                "INSERT OR REPLACE INTO schema_version(version) VALUES (?)",
                (ver,),
            )
        log.info("Schema migration v%d complete", ver)


def current_version(con: sqlite3.Connection) -> int:
    """Return the currently applied schema version (0 if uninitialised)."""
    return _current_version(con)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _current_version(con: sqlite3.Connection) -> int:
    try:
        row = con.execute(
            "SELECT max(version) FROM schema_version"
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except sqlite3.OperationalError:
        return 0
