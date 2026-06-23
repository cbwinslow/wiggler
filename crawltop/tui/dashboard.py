from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Static,
)

from crawltop.config import Settings
from crawltop.core.crawler import CrawlerService
from crawltop.db.repo import CrawlRepo
from crawltop.models import CrawlRun
from crawltop.pipeline.jobs import CrawlJobRunner


CSS = """
Screen {
    layout: vertical;
    background: $surface;
}

#toolbar {
    height: 3;
    padding: 0 1;
    background: $panel;
    border-bottom: solid $accent;
    layout: horizontal;
}

#toolbar Label {
    width: 1fr;
    content-align: center middle;
    color: $text-muted;
}

#toolbar #stats {
    color: $success;
}

#seed-input {
    width: 2fr;
    height: 3;
}

#main {
    height: 1fr;
    layout: horizontal;
}

#left {
    width: 45;
    border-right: solid $panel;
    padding: 0 1;
}

#left Label {
    text-style: bold;
    color: $accent;
    padding-bottom: 1;
}

#runs-table {
    height: 1fr;
}

#right {
    width: 1fr;
    padding: 0 1;
    layout: vertical;
}

#inspector-title {
    text-style: bold;
    color: $accent;
    height: 3;
    border-bottom: solid $panel;
    padding: 1;
}

#page-table {
    height: 1fr;
}

#log {
    height: 12;
    border-top: solid $panel;
}
"""


class CrawlTopApp(App[None]):
    CSS = CSS
    TITLE = "wiggler"
    SUB_TITLE = "htop for crawlers"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_runs", "Refresh"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    selected_run: reactive[CrawlRun | None] = reactive(None)
    active_fetched: reactive[int] = reactive(0)
    active_failed: reactive[int] = reactive(0)
    active_queued: reactive[int] = reactive(0)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.repo = CrawlRepo(settings.db_path)
        self.crawler = CrawlerService(settings.user_agent, settings.max_concurrency)
        self.jobs = CrawlJobRunner(self.repo, self.crawler)

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="  Enter URL and press Enter to start crawl", id="seed-input")

        with Horizontal(id="toolbar"):
            yield Label("[b]workers[/b] --", id="stat-workers")
            yield Label("[b]fetched[/b] 0", id="stat-fetched")
            yield Label("[b]failed[/b] 0", id="stat-failed")
            yield Label("[b]queued[/b] 0", id="stat-queued")
            yield Label("", id="stats")

        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Label(" RUNS")
                yield DataTable(id="runs-table", cursor_type="row")

            with Vertical(id="right"):
                yield Static("Select a run to inspect pages ↓", id="inspector-title")
                yield DataTable(id="page-table", cursor_type="row")

        yield Log(id="log", max_lines=500)
        yield Footer()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        await self.jobs.bootstrap()
        self._setup_runs_table()
        self._setup_page_table()
        await self._reload_runs()
        self._log("wiggler ready — paste a URL and press Enter")

    def _setup_runs_table(self) -> None:
        t: DataTable = self.query_one("#runs-table", DataTable)
        t.add_columns("#", "seed", "status", "fetched", "failed", "created")

    def _setup_page_table(self) -> None:
        t: DataTable = self.query_one("#page-table", DataTable)
        t.add_columns("#", "url", "status", "code", "title", "depth")

    # ── actions ───────────────────────────────────────────────────────────────

    async def action_refresh_runs(self) -> None:
        await self._reload_runs()

    async def action_quit(self) -> None:
        self.exit()

    # ── events ────────────────────────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        seed = event.value.strip()
        if not seed:
            return
        event.input.value = ""
        self._log(f"starting crawl → {seed}")
        self._reset_stats()
        self.run_worker(
            self._crawl_worker(seed),
            exclusive=False,
            name=f"crawl:{seed[:40]}",
        )

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "runs-table":
            row_key = event.row_key
            run_id = int(str(row_key.value))  # type: ignore[union-attr]
            await self._load_pages(run_id)

    # ── workers ───────────────────────────────────────────────────────────────

    async def _crawl_worker(self, seed: str) -> None:
        max_depth = self.settings.crawl_max_depth
        max_pages = self.settings.crawl_max_pages
        async for progress in self.jobs.run_seed(seed, max_depth=max_depth, max_pages=max_pages):
            self.active_fetched = progress.fetched
            self.active_failed = progress.failed
            self.active_queued = progress.queued
            self._update_stat("#stat-fetched", "fetched", progress.fetched)
            self._update_stat("#stat-failed", "failed", progress.failed)
            self._update_stat("#stat-queued", "queued", progress.queued)
            self._log(progress.message)
        await self._reload_runs()
        self._log("crawl complete ✓")

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _reload_runs(self) -> None:
        runs = await self.repo.list_runs()
        t: DataTable = self.query_one("#runs-table", DataTable)
        t.clear()
        for run in runs:
            created = (run.created_at or "")[:16]
            t.add_row(
                str(run.id), run.seed[:30], run.status.value,
                str(run.fetched), str(run.failed), created,
                key=str(run.id),
            )

    async def _load_pages(self, run_id: int) -> None:
        pages = await self.repo.list_pages(run_id)
        t: DataTable = self.query_one("#page-table", DataTable)
        t.clear()
        run = await self.repo.get_run(run_id)
        if run:
            self.query_one("#inspector-title", Static).update(
                f"[b]Run #{run.id}[/b]  {run.seed}  [{run.status.value}]  "
                f"fetched={run.fetched} failed={run.failed}"
            )
        for page in pages:
            title = (page.title or "")[:40]
            url_short = page.url[:55]
            t.add_row(
                str(page.id), url_short, page.status.value,
                str(page.status_code or "-"), title, str(page.depth),
                key=str(page.id),
            )

    def _update_stat(self, selector: str, label: str, value: int) -> None:
        self.query_one(selector, Label).update(f"[b]{label}[/b] {value}")

    def _reset_stats(self) -> None:
        self._update_stat("#stat-fetched", "fetched", 0)
        self._update_stat("#stat-failed", "failed", 0)
        self._update_stat("#stat-queued", "queued", 0)

    def _log(self, message: str) -> None:
        self.query_one("#log", Log).write_line(message)
