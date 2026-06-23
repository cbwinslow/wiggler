"""search_modal.py — FTS search overlay for the Wiggler TUI."""
from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import DataTable, Input, Label
from textual.containers import Vertical


class SearchModal(ModalScreen):
    """Full-text search overlay. Press / to open, Escape to close."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
    ]

    CSS = """
    SearchModal {
        align: center middle;
    }
    #search-container {
        width: 80;
        height: 30;
        border: double $accent;
        background: $surface;
        padding: 1 2;
    }
    #search-input {
        margin-bottom: 1;
    }
    #results-table {
        height: 20;
    }
    """

    def __init__(self, repo) -> None:  # type: ignore[type-arg]
        super().__init__()
        self.repo = repo

    def compose(self) -> ComposeResult:
        with Vertical(id="search-container"):
            yield Label("[bold]Search Pages[/bold] (FTS)")
            yield Input(placeholder="Type to search...", id="search-input")
            yield DataTable(id="results-table", cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("Run", "Title", "URL")

    @on(Input.Changed, "#search-input")
    async def on_search_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        table = self.query_one("#results-table", DataTable)
        table.clear()
        if not query:
            return
        try:
            results = await self.repo.search_pages(query, limit=50)
            for row in results:
                r = dict(row) if not isinstance(row, dict) else row
                table.add_row(
                    str(r.get("run_id", "")),
                    r.get("title") or "",
                    r.get("url") or "",
                )
        except Exception as exc:
            table.add_row("", f"Error: {exc}", "")

    @on(DataTable.RowSelected, "#results-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        self.dismiss(event.row_key)
