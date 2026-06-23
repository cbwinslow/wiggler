from pathlib import Path
import aiosqlite

from crawltop.models import CrawlRun, PageRecord


class CrawlRepo:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def connect(self) -> aiosqlite.Connection:
        return await aiosqlite.connect(self.db_path)

    async def init_db(self, schema_path: Path) -> None:
        async with await self.connect() as db:
            await db.executescript(schema_path.read_text())
            await db.commit()

    async def create_run(self, seed: str) -> int:
        async with await self.connect() as db:
            cursor = await db.execute("INSERT INTO runs(seed, status) VALUES (?, ?)", (seed, "running"))
            await db.commit()
            return int(cursor.lastrowid)

    async def add_page(self, page: PageRecord) -> int:
        async with await self.connect() as db:
            cursor = await db.execute(
                "INSERT INTO pages(run_id, url, status_code, title, content_text) VALUES (?, ?, ?, ?, ?)",
                (page.run_id, page.url, page.status_code, page.title, page.content_text),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def list_runs(self) -> list[CrawlRun]:
        async with await self.connect() as db:
            cursor = await db.execute(
                "SELECT id, seed, status, created_at FROM runs ORDER BY created_at DESC LIMIT 100"
            )
            rows = await cursor.fetchall()
        return [CrawlRun(id=row[0], seed=row[1], status=row[2], created_at=row[3]) for row in rows]
