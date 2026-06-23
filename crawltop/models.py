from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CrawlRun:
    id: int | None
    seed: str
    status: str
    created_at: datetime | None = None


@dataclass(slots=True)
class PageRecord:
    id: int | None
    run_id: int
    url: str
    status_code: int | None
    title: str | None
    content_text: str | None
    fetched_at: datetime | None = None
