# Roadmap

## v0.2 ✔

- Recursive crawl queue with domain/depth/page limits.
- WAL + FTS5 SQLite schema.
- Real-time Textual dashboard: runs table, page inspector, stat toolbar, live log.
- Async repo helpers: enqueue/dequeue/counter/event log.
- Domain-scoped crawl and same-domain link filtering.

## v0.3 ✔

- Search provider layer (Exa, Brave) with auto-registry.
- Full-text search modal across saved pages in the TUI (/).
- Page detail modal: full extracted text, scrollable, Markdown-rendered.
- robots.txt parser + per-domain crawl policy + TOS blocklist.
- Export run to Markdown / JSON (RunExporter).
- docs/tos_notes.md per-domain policy log.
- Tests: test_policy.py, test_export.py.

## v0.4 ✔

- Qdrant local mode vector store (on-disk persistence, cosine similarity).
- Text chunker + async Embedder (OpenAI-compatible + sentence-transformers local).
- Open Skill interface + SkillRegistry (community-extensible plugin pattern).
- Built-in skills: CleanerSkill, CuratorSkill, LinkerSkill, QASkill.
- AgentRunner: configurable sequential skill pipeline with graceful LLM fallback.
- annotate_page / annotate_run pipeline: agents + SQLite persist + Qdrant embed.
- docs/agents.md: full skill documentation and custom skill guide.
- Tests: test_agents.py (cleaner, registry, runner, chunker).

## v0.5 ✔

- `crawltop/core/policy_config.py`: per-domain crawl policy config (YAML/JSON, rate limits, depth, TOS flags).
- `crawltop/core/robots.py`: robots.txt fetch + parse + TTL cache.
- `crawltop/core/table_extractor.py`: HTML `<table>` extraction via selectolax → normalized list-of-dict records with caption, headers, rows.
- `crawltop/core/entity_linker.py`: MLB entity resolution (30-team seed index + DB player lookup) using trigram Dice similarity; zero external calls.
- `crawltop/db/schema.py`: Python migration manager (v1 → v2); adds `players`, `extracted_tables`, `entity_links` tables + FTS5 virtual table + sync triggers.
- `crawltop/pipeline/exporter.py`: advanced multi-format export (JSON, JSONL, CSV, Markdown, Parquet) with optional embedded tables + entity links; CLI entrypoint.
- Tests: test_table_extractor.py, test_entity_linker.py, test_schema.py, test_exporter.py.

## v0.6 (planned)

- Scheduled / recurring crawl jobs (cron-style via APScheduler).
- Multi-site crawl orchestration: parallel domain workers with shared queue.
- TUI: live per-domain bandwidth + entity-link heat-map panel.
- MLB standings / box-score pipeline: ingest + normalise + deduplicate via entity linker.
- Parquet + DuckDB analytics integration (query extracted tables in-app).
- REST micro-API (FastAPI) for headless operation and CI integration.
