# Roadmap

## v0.2 ✓

- Recursive crawl queue with domain/depth/page limits.
- WAL + FTS5 SQLite schema.
- Real-time Textual dashboard: runs table, page inspector, stat toolbar, live log.
- Async repo helpers: enqueue/dequeue/counter/event log.
- Domain-scoped crawl and same-domain link filtering.

## v0.3 ✓

- Search provider layer (Exa, Brave) with auto-registry.
- Full-text search modal across saved pages in the TUI (/).
- Page detail modal: full extracted text, scrollable, Markdown-rendered.
- robots.txt parser + per-domain crawl policy + TOS blocklist.
- Export run to Markdown / JSON (RunExporter).
- docs/tos_notes.md per-domain policy log.
- Tests: test_policy.py, test_export.py.

## v0.4 ✓

- Qdrant local mode vector store (on-disk persistence, cosine similarity).
- Text chunker + async Embedder (OpenAI-compatible + sentence-transformers local).
- Open Skill interface + SkillRegistry (community-extensible plugin pattern).
- Built-in skills: CleanerSkill, CuratorSkill, LinkerSkill, QASkill.
- AgentRunner: configurable sequential skill pipeline with graceful LLM fallback.
- annotate_page / annotate_run pipeline: agents + SQLite persist + Qdrant embed.
- docs/agents.md: full skill documentation + custom skill guide.
- Tests: test_agents.py (cleaner, registry, runner, chunker).

## v0.5

- Multi-site crawl policies with per-domain config.
- Table extraction from HTML into structured SQLite rows.
- Entity linking across runs (players, orgs, topics).
- Export to CSV / Parquet for downstream dbt/PostgreSQL ingestion.
- Plugin SDK: open skill and provider interface for contributors.
- CrewAI / LangChain adapter as optional orchestration layer.
- Image capture and OCR for pages with key visual content.
