# Wiggler Agent Skills

Wiggler uses a configurable, open skill pipeline to enrich crawled pages after ingestion.
Skills are the atomic units of agent capability and can be contributed by the community.

---

## Architecture

```
Crawled page dict
        ↓
  AgentRunner.run_page()
        ↓
  [cleaner] → [curator] → [linker] → [qa]
        ↓
  Enriched page dict (saved to SQLite + Qdrant)
```

- **Skills are sequential.** Each skill receives the page dict enriched by prior skills.
- **Skills are optional.** LLM-powered skills skip gracefully when no API key is configured.
- **Skills are open.** Subclass `Skill`, set `name`, implement `run()`, and register with `@SkillRegistry.register`.

---

## Built-in Skills

### `cleaner` (CleanerSkill)
- **Requires LLM:** No
- **Input:** `raw_text` or `clean_text`
- **Output:** `clean_text`
- **What it does:** Strips boilerplate (newsletter prompts, cookie notices, copyright lines, short nav fragments), normalises whitespace, drops near-empty lines.

### `curator` (CuratorSkill)
- **Requires LLM:** Yes (OpenAI-compatible)
- **Input:** `clean_text`
- **Output:** `summary`, `tags`, `title`, `publish_date`, `author`, `confidence`
- **What it does:** Generates a concise 2-4 sentence summary, 3-8 tags, and structured metadata via LLM.
- **Configurable:** `curator_model` setting, custom `prompt`.

### `linker` (LinkerSkill)
- **Requires LLM:** Yes (OpenAI-compatible)
- **Input:** `clean_text`
- **Output:** `entities` list — `[{name, type, context}]`
- **What it does:** Extracts named entities (PERSON, TEAM, LEAGUE, STADIUM, ORGANIZATION, LOCATION, EVENT) from page text. Future: links to canonical entity IDs in the wiggler entity graph.
- **Configurable:** `linker_model` setting.

### `qa` (QASkill)
- **Requires LLM:** Yes (OpenAI-compatible)
- **Input:** `clean_text`, `curator_output`
- **Output:** `notes` (PASS/FAIL), `confidence`
- **What it does:** Verifies that curator output is factually consistent with the source text. Flags hallucinations, wrong tags, incorrect titles.
- **Configurable:** `qa_model` setting.

---

## Configuration

All LLM-powered skills read from the settings dict (populated from `.env` or config):

```ini
# .env
OPENAI_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1   # or Ollama, LM Studio, etc.
CURATOR_MODEL=gpt-4o-mini
LINKER_MODEL=gpt-4o-mini
QA_MODEL=gpt-4o-mini
```

Set `LLM_BASE_URL` to an OpenAI-compatible endpoint to use Ollama, LM Studio, or any local model.

---

## Writing a Custom Skill

```python
from crawltop.agents.skills import Skill, SkillRegistry, SkillResult

@SkillRegistry.register
class MySportsSkill(Skill):
    name = "my_sports_skill"
    description = "Extracts game scores and box score data."
    version = "0.1.0"
    author = "your-github-handle"

    async def run(self, page: dict, settings: dict) -> SkillResult:
        text = page.get("clean_text") or ""
        # ... your logic ...
        return SkillResult(
            skill_name=self.name,
            success=True,
            tags=["box-score", "mlb"],
            notes="Found 3 game scores.",
        )
```

Then add `"my_sports_skill"` to your pipeline list in config or pass it to `AgentRunner(pipeline=[...])`.

---

## Pipeline Configuration

```python
from crawltop.agents.runner import AgentRunner

runner = AgentRunner(
    settings={"openai_api_key": "..."},
    pipeline=["cleaner", "curator", "linker", "qa", "my_sports_skill"],
)
results = await runner.run_page(page_dict)
```

---

_Last updated: v0.4_
