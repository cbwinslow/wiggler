# Roadmap

## v0.2 ✓

- Recursive crawl queue with domain/depth/page limits.
- WAL + FTS5 SQLite schema.
- Real-time Textual dashboard: runs table, page inspector, stat toolbar, live log.
- Async repo helpers: enqueue/dequeue/counter/event log.
- Domain-scoped crawl and same-domain link filtering.

## v0.3

- Search provider (Exa, Brave).
- Full-text search across saved pages in the TUI.
- Page detail view: full extracted text, links, depth.
- robots.txt parser + per-domain crawl policy.
- Export run to Markdown / JSON.

## v0.4

- Optional Qdrant local mode for semantic search.
- Configurable agent skills (cleaner, curator, QA, linker).
- Agent results stored as run annotations.
- CrewAI / LangChain adapter plugged into pipeline.

## v0.5

- Search-term seed via Exa/Brave → URL fan-out.
- Table and image extraction.
- Multi-run comparison and entity linking.
