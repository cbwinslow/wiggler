from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Log, Static

from crawltop.config import Settings
from crawltop.core.crawler import CrawlerService
from crawltop.db.repo import CrawlRepo
from crawltop.pipeline.jobs import CrawlJobRunner


class CrawlTopApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    #left, #right { width: 1fr; border: round $surface; padding: 1; }
    #log { height: 10; }
    """

    BINDINGS = [("q", "quit", "Quit")]
    last_run_id = reactive[int | None](None)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.repo = CrawlRepo(settings.db_path)
        self.crawler = CrawlerService(settings.user_agent)
        self.jobs = CrawlJobRunner(self.repo, self.crawler, Path(__file__).resolve().parent.parent / "db" / "schema.sql")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Input(placeholder="Enter a URL and press Enter", id="seed-input")
        with Horizontal(id="main"):
            with Container(id="left"):
                yield Static("Runs", id="runs-title")
                yield Static("No runs yet.", id="runs-list")
            with Container(id="right"):
                yield Static("Inspector", id="inspector-title")
                yield Static("Select or create a crawl run.", id="inspector-body")
        yield Log(id="log")
        yield Footer()

    async def on_mount(self) -> None:
        await self.jobs.bootstrap()
        self.write_log("crawltop ready")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        seed = event.value.strip()
        if not seed:
            return
        self.write_log(f"starting crawl: {seed}")
        run_id = await self.jobs.run_seed(seed)
        self.last_run_id = run_id
        self.query_one("#inspector-body", Static).update(f"Completed run #{run_id} for {seed}")
        self.query_one("#runs-list", Static).update(f"Latest run: #{run_id}\n{seed}")
        event.input.value = ""

    def write_log(self, message: str) -> None:
        self.query_one("#log", Log).write_line(message)
