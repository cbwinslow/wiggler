from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageStatus(str, Enum):
    PENDING = "pending"
    FETCHED = "fetched"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class CrawlRun:
    id: int | None
    seed: str
    status: RunStatus
    depth: int = 1
    max_pages: int = 50
    fetched: int = 0
    failed: int = 0
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class PageRecord:
    id: int | None
    run_id: int
    url: str
    status: PageStatus = PageStatus.PENDING
    status_code: int | None = None
    title: str | None = None
    content_text: str | None = None
    depth: int = 0
    fetched_at: str | None = None


@dataclass(slots=True)
class DiscoveredUrl:
    id: int | None
    run_id: int
    url: str
    depth: int
    status: str = "pending"


@dataclass(slots=True)
class CrawlEvent:
    id: int | None
    run_id: int
    level: str
    message: str
    created_at: str | None = None
