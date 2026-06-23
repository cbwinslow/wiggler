from __future__ import annotations

from pathlib import Path

import aiosqlite

from crawltop.models import CrawlEvent, CrawlRun, DiscoveredUrl, PageRecord, PageStatus, RunStatus

_SCHEMA = Path(__file__).with_name("schema.sql")


class CrawlRepo:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def _connect(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.db_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        return db

    async def init_db(self) -> None:
        async with await self._connect() as db:
            await db.executescript(_SCHEMA.read_text())
            await db.commit()

    # ── runs ──────────────────────────────────────────────────────────────────

    async def create_run(self, seed: str, depth: int = 1, max_pages: int = 50) -> int:
        async with await self._connect() as db:
            cur = await db.execute(
                "INSERT INTO runs(seed, status, depth, max_pages) VALUES (?,?,?,?)",
                (seed, RunStatus.RUNNING, depth, max_pages),
            )
            await db.commit()
            return int(cur.lastrowid)  # type: ignore[arg-type]

    async def update_run_status(self, run_id: int, status: RunStatus) -> None:
        async with await self._connect() as db:
            await db.execute(
                "UPDATE runs SET status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
                (status, run_id),
            )
            await db.commit()

    async def increment_run_counters(self, run_id: int, fetched: int = 0, failed: int = 0) -> None:
        async with await self._connect() as db:
            await db.execute(
                "UPDATE runs SET fetched=fetched+?, failed=failed+?, "
                "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
                (fetched, failed, run_id),
            )
            await db.commit()

    async def list_runs(self, limit: int = 100) -> list[CrawlRun]:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT id, seed, status, depth, max_pages, fetched, failed, created_at, updated_at "
                "FROM runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
        return [
            CrawlRun(
                id=r["id"], seed=r["seed"], status=RunStatus(r["status"]),
                depth=r["depth"], max_pages=r["max_pages"],
                fetched=r["fetched"], failed=r["failed"],
                created_at=r["created_at"], updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def get_run(self, run_id: int) -> CrawlRun | None:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT id, seed, status, depth, max_pages, fetched, failed, created_at, updated_at "
                "FROM runs WHERE id=?", (run_id,)
            )
            row = await cur.fetchone()
        if not row:
            return None
        return CrawlRun(
            id=row["id"], seed=row["seed"], status=RunStatus(row["status"]),
            depth=row["depth"], max_pages=row["max_pages"],
            fetched=row["fetched"], failed=row["failed"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    # ── pages ─────────────────────────────────────────────────────────────────

    async def add_page(self, page: PageRecord) -> int:
        async with await self._connect() as db:
            cur = await db.execute(
                "INSERT INTO pages(run_id, url, status, status_code, title, content_text, depth) "
                "VALUES (?,?,?,?,?,?,?)",
                (page.run_id, page.url, page.status, page.status_code, page.title, page.content_text, page.depth),
            )
            await db.commit()
            return int(cur.lastrowid)  # type: ignore[arg-type]

    async def list_pages(self, run_id: int, limit: int = 200) -> list[PageRecord]:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT id, run_id, url, status, status_code, title, content_text, depth, fetched_at "
                "FROM pages WHERE run_id=? ORDER BY id ASC LIMIT ?",
                (run_id, limit),
            )
            rows = await cur.fetchall()
        return [
            PageRecord(
                id=r["id"], run_id=r["run_id"], url=r["url"],
                status=PageStatus(r["status"]), status_code=r["status_code"],
                title=r["title"], content_text=r["content_text"],
                depth=r["depth"], fetched_at=r["fetched_at"],
            )
            for r in rows
        ]

    async def search_pages(self, query: str, limit: int = 50) -> list[PageRecord]:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT p.id, p.run_id, p.url, p.status, p.status_code, p.title, "
                "p.content_text, p.depth, p.fetched_at "
                "FROM pages p JOIN pages_fts f ON p.id = f.rowid "
                "WHERE pages_fts MATCH ? LIMIT ?",
                (query, limit),
            )
            rows = await cur.fetchall()
        return [
            PageRecord(
                id=r["id"], run_id=r["run_id"], url=r["url"],
                status=PageStatus(r["status"]), status_code=r["status_code"],
                title=r["title"], content_text=r["content_text"],
                depth=r["depth"], fetched_at=r["fetched_at"],
            )
            for r in rows
        ]

    # ── discovered urls ───────────────────────────────────────────────────────

    async def enqueue_urls(self, run_id: int, urls: list[tuple[str, int]]) -> None:
        """urls: list of (url, depth) tuples. Ignores duplicates per run."""
        async with await self._connect() as db:
            await db.executemany(
                "INSERT OR IGNORE INTO discovered_urls(run_id, url, depth) VALUES (?,?,?)",
                [(run_id, url, depth) for url, depth in urls],
            )
            await db.commit()

    async def dequeue_url(self, run_id: int) -> DiscoveredUrl | None:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT id, run_id, url, depth, status FROM discovered_urls "
                "WHERE run_id=? AND status='pending' ORDER BY depth ASC, id ASC LIMIT 1",
                (run_id,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            await db.execute("UPDATE discovered_urls SET status='processing' WHERE id=?", (row["id"],))
            await db.commit()
        return DiscoveredUrl(id=row["id"], run_id=row["run_id"], url=row["url"], depth=row["depth"])

    async def mark_url_done(self, url_id: int, status: str = "done") -> None:
        async with await self._connect() as db:
            await db.execute("UPDATE discovered_urls SET status=? WHERE id=?", (status, url_id))
            await db.commit()

    async def queue_size(self, run_id: int) -> int:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM discovered_urls WHERE run_id=? AND status='pending'",
                (run_id,),
            )
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    # ── events ────────────────────────────────────────────────────────────────

    async def log_event(self, run_id: int, message: str, level: str = "info") -> None:
        async with await self._connect() as db:
            await db.execute(
                "INSERT INTO crawl_events(run_id, level, message) VALUES (?,?,?)",
                (run_id, level, message),
            )
            await db.commit()

    async def list_events(self, run_id: int, limit: int = 200) -> list[CrawlEvent]:
        async with await self._connect() as db:
            cur = await db.execute(
                "SELECT id, run_id, level, message, created_at FROM crawl_events "
                "WHERE run_id=? ORDER BY id DESC LIMIT ?",
                (run_id, limit),
            )
            rows = await cur.fetchall()
        return [
            CrawlEvent(id=r["id"], run_id=r["run_id"], level=r["level"],
                       message=r["message"], created_at=r["created_at"])
            for r in rows
        ]
