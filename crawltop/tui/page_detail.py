"""page_detail.py — Full-screen page content inspector modal."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown, Footer
from textual.containers import ScrollableContainer, Vertical


class PageDetailModal(ModalScreen):
    """Display full extracted/cleaned content for a single crawled page."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    CSS = """
    PageDetailModal {
        align: center middle;
    }
    #detail-container {
        width: 90%;
        height: 85%;
        border: double $accent;
        background: $surface;
        padding: 1 2;
    }
    #page-title {
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }
    #page-url {
        color: $text-muted;
        margin-bottom: 1;
    }
    #content-scroll {
        height: 1fr;
        border: solid $panel;
    }
    """

    def __init__(self, page: dict) -> None:
        super().__init__()
        self.page = page

    def compose(self) -> ComposeResult:
        p = self.page
        title = p.get("title") or "Untitled"
        url = p.get("url") or ""
        content = p.get("clean_text") or p.get("raw_text") or "*(no content extracted)*"

        with Vertical(id="detail-container"):
            yield Label(f"[bold]{title}[/bold]", id="page-title")
            yield Label(f"[link={url}]{url}[/link]", id="page-url")
            with ScrollableContainer(id="content-scroll"):
                yield Markdown(content)
        yield Footer()
