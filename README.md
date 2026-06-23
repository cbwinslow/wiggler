# crawltop

`crawltop` is a standalone TUI web crawler/scraper for Python built around Textual, HTTPX, selectolax, and SQLite.

## Goals

- Fast, lightweight, local-first crawling.
- Clean TUI that feels like `htop` for crawl jobs.
- SQLite as the operational database.
- Optional vector search and AI enrichment later.
- Pluggable providers, agents, and skills.

## v0 starter scope

- Start a crawl from a URL.
- Persist runs, pages, links, and crawl events in SQLite.
- Show runs and page history in a Textual UI.
- Keep extraction deterministic first; AI enrichment remains optional.

## Project layout

- `crawltop/app.py` - Textual entrypoint.
- `crawltop/config.py` - typed settings loader.
- `crawltop/models.py` - core dataclasses.
- `crawltop/db/` - SQLite schema and repository helpers.
- `crawltop/core/` - crawler, parser, and cleaner primitives.
- `crawltop/tui/` - screens, widgets, actions.
- `crawltop/pipeline/` - crawl job orchestration.
- `crawltop/agents/` - agent interfaces and future skills.
- `crawltop/providers/` - search / LLM / embeddings adapters.
- `crawltop/vector/` - optional vector integration.

## Next steps

1. Create the SQLite migrations and repository methods.
2. Wire the `CrawlerService` into the dashboard screen.
3. Implement page extraction and link normalization.
4. Add search providers and optional summarization agents.
