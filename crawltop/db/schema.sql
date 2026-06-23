PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  seed        TEXT    NOT NULL,
  status      TEXT    NOT NULL DEFAULT 'queued',
  depth       INTEGER NOT NULL DEFAULT 1,
  max_pages   INTEGER NOT NULL DEFAULT 50,
  fetched     INTEGER NOT NULL DEFAULT 0,
  failed      INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS pages (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id       INTEGER NOT NULL,
  url          TEXT    NOT NULL,
  status       TEXT    NOT NULL DEFAULT 'pending',
  status_code  INTEGER,
  title        TEXT,
  content_text TEXT,
  depth        INTEGER NOT NULL DEFAULT 0,
  fetched_at   TEXT    DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS discovered_urls (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id  INTEGER NOT NULL,
  url     TEXT    NOT NULL,
  depth   INTEGER NOT NULL DEFAULT 0,
  status  TEXT    NOT NULL DEFAULT 'pending',
  FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS crawl_events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id     INTEGER NOT NULL,
  level      TEXT    NOT NULL DEFAULT 'info',
  message    TEXT    NOT NULL,
  created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runs_created_at       ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pages_run_id          ON pages(run_id);
CREATE INDEX IF NOT EXISTS idx_pages_url             ON pages(url);
CREATE INDEX IF NOT EXISTS idx_disc_run_status       ON discovered_urls(run_id, status);
CREATE INDEX IF NOT EXISTS idx_events_run_id         ON crawl_events(run_id);

CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
  title,
  content_text,
  content=pages,
  content_rowid=id
);
