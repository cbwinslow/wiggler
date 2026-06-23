# wiggler

`wiggler` is a standalone TUI web crawler/scraper for Python built around
[Textual](https://textual.textualize.io/), [HTTPX](https://www.python-httpx.org/),
[selectolax](https://github.com/rushter/selectolax), and SQLite.

## Goals

- Fast, lightweight, local-first crawling.
- Clean TUI that feels like `htop` for crawl jobs.
- SQLite as the operational database (WAL mode + FTS5).
- Optional AI enrichment and vector search layered on top.
- Pluggable providers, agents, and skills.

## Install

```bash
pip install -e .
# or with AI extras
pip install -e ".[ai]"
```

## Usage

```bash
wiggler
```

Paste a URL into the input bar and press `Enter` to start a crawl.  
Select a run in the left pane to inspect pages in the right pane.  
Press `r` to refresh the runs list, `q` to quit.

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `CRAWLTOP_DB_PATH` | `./data/wiggler.db` | SQLite database path |
| `CRAWLTOP_MAX_CONCURRENCY` | `10` | Max async workers |
| `CRAWLTOP_CRAWL_MAX_DEPTH` | `1` | Link follow depth |
| `CRAWLTOP_CRAWL_MAX_PAGES` | `50` | Max pages per run |
| `CRAWLTOP_USER_AGENT` | wiggler/0.2 | HTTP user agent |

## Project layout

```
wiggler/
├── crawltop/
│   ├── app.py            # entrypoint
│   ├── config.py         # pydantic settings
│   ├── models.py         # dataclasses / enums
│   ├── core/             # http, parser, cleaner, crawler
│   ├── db/               # schema.sql + async repo
│   ├── pipeline/         # crawl job orchestration
│   ├── tui/              # Textual screens + widgets
│   ├── agents/           # agent interface stubs
│   ├── providers/        # search / LLM / embedding adapters
│   └── vector/           # optional Qdrant integration
├── tests/
├── docs/
├── pyproject.toml
└── .env.example
```

## Roadmap

### v0.2 ✓
- Recursive crawl queue with domain/depth/page limits.
- WAL-mode SQLite with FTS5 full-text search index.
- Real-time Textual dashboard: runs table, page inspector, live event log.
- Async semaphore-controlled concurrent fetching.
- Async repo layer with enqueue/dequeue/counter helpers.

### v0.3
- Search provider integration (Exa, Brave, Google).
- Page detail screen with full extracted content.
- Export to Markdown / JSON.
- robots.txt and TOS per-domain policy config.

### v0.4
- Optional Qdrant embeddings and semantic search.
- Configurable agent skills (cleaner, curator, QA, linker).
- CrewAI / LangChain adapter.
