"""test_export.py — Tests for RunExporter."""
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from crawltop.pipeline.export import RunExporter


def _make_repo(run_data: dict, pages: list, events: list):
    """Build a mock repo that returns canned data."""
    repo = MagicMock()
    run_obj = MagicMock()
    run_obj.__dict__ = run_data
    repo.get_run = AsyncMock(return_value=run_obj)

    page_objs = []
    for p in pages:
        m = MagicMock()
        m.__dict__ = p
        page_objs.append(m)
    repo.list_pages = AsyncMock(return_value=page_objs)

    event_objs = []
    for e in events:
        m = MagicMock()
        m.__dict__ = e
        event_objs.append(m)
    repo.list_events = AsyncMock(return_value=event_objs)
    return repo


@pytest.mark.asyncio
async def test_to_json_creates_file():
    repo = _make_repo(
        run_data={"id": 1, "seed_url": "https://example.com", "started_at": "2026-01-01"},
        pages=[{"url": "https://example.com/a", "title": "Page A", "clean_text": "hello"}],
        events=[{"event": "fetch", "url": "https://example.com/a"}],
    )
    exporter = RunExporter(repo)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "run.json"
        result = await exporter.to_json(1, dest=dest)
        assert result.exists()
        data = json.loads(result.read_text())
        assert data["run"]["seed_url"] == "https://example.com"
        assert len(data["pages"]) == 1


@pytest.mark.asyncio
async def test_to_markdown_creates_file():
    repo = _make_repo(
        run_data={"id": 2, "seed_url": "https://example.com", "started_at": "2026-01-01"},
        pages=[{"url": "https://example.com/b", "title": "Page B", "clean_text": "world"}],
        events=[],
    )
    exporter = RunExporter(repo)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "run.md"
        result = await exporter.to_markdown(2, dest=dest)
        assert result.exists()
        content = result.read_text()
        assert "Page B" in content
        assert "https://example.com/b" in content
