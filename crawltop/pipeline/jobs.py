from pathlib import Path

from crawltop.core.crawler import CrawlerService
from crawltop.db.repo import CrawlRepo
from crawltop.models import PageRecord


class CrawlJobRunner:
    def __init__(self, repo: CrawlRepo, crawler: CrawlerService, schema_path: Path):
        self.repo = repo
        self.crawler = crawler
        self.schema_path = schema_path

    async def bootstrap(self) -> None:
        await self.repo.init_db(self.schema_path)

    async def run_seed(self, seed_url: str) -> int:
        run_id = await self.repo.create_run(seed_url)
        result = await self.crawler.fetch_one(seed_url)
        await self.repo.add_page(
            PageRecord(
                id=None,
                run_id=run_id,
                url=result.url,
                status_code=result.status_code,
                title=result.title,
                content_text=result.text,
            )
        )
        return run_id
