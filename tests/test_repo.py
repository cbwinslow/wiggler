import asyncio
from pathlib import Path

import pytest

from crawltop.db.repo import CrawlRepo
from crawltop.models import PageRecord, PageStatus


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.mark.asyncio
async def test_create_run_and_list(tmp_db: Path) -> None:
    repo = CrawlRepo(tmp_db)
    await repo.init_db()
    run_id = await repo.create_run("https://example.com")
    assert run_id > 0
    runs = await repo.list_runs()
    assert any(r.id == run_id for r in runs)


@pytest.mark.asyncio
async def test_queue_and_dequeue(tmp_db: Path) -> None:
    repo = CrawlRepo(tmp_db)
    await repo.init_db()
    run_id = await repo.create_run("https://example.com")
    await repo.enqueue_urls(run_id, [("https://example.com", 0), ("https://example.com/about", 1)])
    item = await repo.dequeue_url(run_id)
    assert item is not None
    assert item.url in ("https://example.com", "https://example.com/about")


@pytest.mark.asyncio
async def test_add_and_list_pages(tmp_db: Path) -> None:
    repo = CrawlRepo(tmp_db)
    await repo.init_db()
    run_id = await repo.create_run("https://example.com")
    await repo.add_page(
        PageRecord(id=None, run_id=run_id, url="https://example.com",
                   status=PageStatus.FETCHED, status_code=200, title="Home",
                   content_text="hello world", depth=0)
    )
    pages = await repo.list_pages(run_id)
    assert len(pages) == 1
    assert pages[0].title == "Home"
