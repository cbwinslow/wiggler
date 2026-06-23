from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from crawltop.core.crawler import CrawlerService
from crawltop.db.repo import CrawlRepo
from crawltop.models import PageRecord, PageStatus, RunStatus


@dataclass
class CrawlProgress:
    run_id: int
    url: str
    fetched: int
    failed: int
    queued: int
    message: str


class CrawlJobRunner:
    def __init__(self, repo: CrawlRepo, crawler: CrawlerService):
        self.repo = repo
        self.crawler = crawler

    async def bootstrap(self) -> None:
        await self.repo.init_db()

    async def run_seed(
        self,
        seed_url: str,
        max_depth: int = 1,
        max_pages: int = 50,
        same_domain_only: bool = True,
    ) -> AsyncGenerator[CrawlProgress, None]:
        run_id = await self.repo.create_run(seed_url, depth=max_depth, max_pages=max_pages)
        await self.repo.log_event(run_id, f"run started seed={seed_url}")
        await self.repo.enqueue_urls(run_id, [(seed_url, 0)])

        fetched = 0
        failed = 0

        while True:
            if fetched + failed >= max_pages:
                break
            item = await self.repo.dequeue_url(run_id)
            if not item:
                break

            result = await self.crawler.fetch_one(item.url)

            if result.ok:
                page = PageRecord(
                    id=None, run_id=run_id, url=result.url,
                    status=PageStatus.FETCHED,
                    status_code=result.status_code,
                    title=result.title, content_text=result.text,
                    depth=item.depth,
                )
                await self.repo.add_page(page)
                await self.repo.mark_url_done(item.id)  # type: ignore[arg-type]
                await self.repo.increment_run_counters(run_id, fetched=1)
                fetched += 1
                await self.repo.log_event(run_id, f"fetched [{result.status_code}] {result.url}")

                # enqueue child links within depth limit
                next_depth = item.depth + 1
                if next_depth <= max_depth:
                    child_links = [
                        (link, next_depth)
                        for link in result.links
                        if not same_domain_only or CrawlerService.same_domain(seed_url, link)
                    ]
                    await self.repo.enqueue_urls(run_id, child_links)
            else:
                page = PageRecord(
                    id=None, run_id=run_id, url=item.url,
                    status=PageStatus.FAILED, depth=item.depth,
                )
                await self.repo.add_page(page)
                await self.repo.mark_url_done(item.id, "failed")  # type: ignore[arg-type]
                await self.repo.increment_run_counters(run_id, failed=1)
                failed += 1
                await self.repo.log_event(run_id, f"failed {item.url}: {result.error}", level="error")

            queued = await self.repo.queue_size(run_id)
            yield CrawlProgress(
                run_id=run_id, url=result.url,
                fetched=fetched, failed=failed, queued=queued,
                message=f"{'OK' if result.ok else 'ERR'} {result.url}",
            )

        await self.repo.update_run_status(run_id, RunStatus.DONE)
        await self.repo.log_event(run_id, f"run done fetched={fetched} failed={failed}")
