"""crawltop/core/table_extractor.py

HTML table extraction for structured MLB data (standings, stats, schedules).
Uses selectolax for fast parsing. Returns normalized list-of-dict records.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from selectolax.parser import HTMLParser, Node
except ImportError:  # pragma: no cover
    HTMLParser = None  # type: ignore
    Node = None  # type: ignore


@dataclass
class ExtractedTable:
    """A single HTML table parsed into headers + rows."""

    caption: str = ""
    headers: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    source_url: str = ""
    table_index: int = 0

    # ------------------------------------------------------------------ #
    # convenience
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:  # noqa: D105
        return len(self.rows)

    def to_list(self) -> list[dict[str, Any]]:
        """Return rows as a plain list of dicts (for JSON / DB insert)."""
        return self.rows


class TableExtractor:
    """Extract all <table> elements from an HTML string.

    Parameters
    ----------
    min_cols:
        Ignore tables with fewer than this many columns (skips nav tables).
    min_rows:
        Ignore tables with fewer data rows than this.
    header_row_index:
        Which <tr> to treat as the header (0-based). Defaults to 0.
    """

    def __init__(
        self,
        min_cols: int = 2,
        min_rows: int = 1,
        header_row_index: int = 0,
    ) -> None:
        self.min_cols = min_cols
        self.min_rows = min_rows
        self.header_row_index = header_row_index

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def extract(self, html: str, source_url: str = "") -> list[ExtractedTable]:
        """Parse *html* and return a list of :class:`ExtractedTable`."""
        if HTMLParser is None:
            raise RuntimeError(
                "selectolax is required: pip install selectolax"
            )
        tree = HTMLParser(html)
        results: list[ExtractedTable] = []
        for idx, table_node in enumerate(tree.css("table")):
            extracted = self._parse_table(table_node, idx, source_url)
            if extracted is None:
                continue
            results.append(extracted)
        return results

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _parse_table(
        self, node: Any, idx: int, source_url: str
    ) -> ExtractedTable | None:
        """Convert a single table node -> ExtractedTable or None."""
        caption = self._get_caption(node)
        all_rows = node.css("tr")
        if len(all_rows) <= self.header_row_index:
            return None

        headers = self._extract_headers(all_rows[self.header_row_index])
        if len(headers) < self.min_cols:
            return None

        data_rows = all_rows[self.header_row_index + 1 :]
        rows: list[dict[str, Any]] = []
        for tr in data_rows:
            cells = [self._cell_text(c) for c in tr.css("td")]
            if not cells:
                continue  # skip header-like rows inside tbody
            # Pad / trim cells to match header length
            while len(cells) < len(headers):
                cells.append("")
            cells = cells[: len(headers)]
            rows.append(dict(zip(headers, cells)))

        if len(rows) < self.min_rows:
            return None

        return ExtractedTable(
            caption=caption,
            headers=headers,
            rows=rows,
            source_url=source_url,
            table_index=idx,
        )

    @staticmethod
    def _get_caption(node: Any) -> str:
        cap = node.css_first("caption")
        return cap.text(strip=True) if cap else ""

    @staticmethod
    def _extract_headers(row: Any) -> list[str]:
        """Return header text from <th> cells; fall back to <td> if no <th>."""
        ths = row.css("th")
        if ths:
            return [TableExtractor._cell_text(th) for th in ths]
        tds = row.css("td")
        return [TableExtractor._cell_text(td) for td in tds]

    @staticmethod
    def _cell_text(node: Any) -> str:
        """Return stripped text content of a cell node."""
        return node.text(strip=True, separator=" ")


# ------------------------------------------------------------------ #
# Convenience helper
# ------------------------------------------------------------------ #
def extract_tables(
    html: str,
    source_url: str = "",
    min_cols: int = 2,
    min_rows: int = 1,
) -> list[ExtractedTable]:
    """Module-level shortcut for :class:`TableExtractor`."""
    return TableExtractor(
        min_cols=min_cols, min_rows=min_rows
    ).extract(html, source_url=source_url)
