"""export.py — Export a crawl run to JSON or Markdown."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class RunExporter:
    """Export run data from SQLite to JSON or Markdown files."""

    def __init__(self, repo) -> None:  # type: ignore[type-arg]
        self.repo = repo

    async def to_json(self, run_id: int, dest: Optional[Path] = None) -> Path:
        """Export full run + pages + events as a JSON file."""
        run = await self.repo.get_run(run_id)
        pages = await self.repo.list_pages(run_id)
        events = await self.repo.list_events(run_id)

        payload = {
            "run": run.__dict__ if hasattr(run, "__dict__") else dict(run),
            "pages": [
                p.__dict__ if hasattr(p, "__dict__") else dict(p) for p in pages
            ],
            "events": [
                e.__dict__ if hasattr(e, "__dict__") else dict(e) for e in events
            ],
        }

        if dest is None:
            dest = Path(f"wiggler_run_{run_id}_{_ts()}.json")

        dest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return dest

    async def to_markdown(self, run_id: int, dest: Optional[Path] = None) -> Path:
        """Export curated page content as a Markdown document."""
        run = await self.repo.get_run(run_id)
        pages = await self.repo.list_pages(run_id)

        run_dict = run.__dict__ if hasattr(run, "__dict__") else dict(run)
        lines = [
            f"# Wiggler Run {run_id}",
            f"",
            f"**Seed:** {run_dict.get('seed_url', 'N/A')}  ",
            f"**Started:** {run_dict.get('started_at', 'N/A')}  ",
            f"**Pages:** {len(pages)}",
            f"",
            "---",
            f"",
        ]

        for i, page in enumerate(pages, 1):
            p = page.__dict__ if hasattr(page, "__dict__") else dict(page)
            title = p.get("title") or p.get("url", "Untitled")
            url = p.get("url", "")
            snippet = (p.get("clean_text") or p.get("raw_text") or "")[:500]
            lines += [
                f"## {i}. {title}",
                f"",
                f"**URL:** {url}  ",
                f"",
                snippet,
                f"",
                "---",
                f"",
            ]

        if dest is None:
            dest = Path(f"wiggler_run_{run_id}_{_ts()}.md")

        dest.write_text("\n".join(lines), encoding="utf-8")
        return dest


def _ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
