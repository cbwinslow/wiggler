"""tests/test_table_extractor.py - unit tests for TableExtractor."""
import pytest

pytest.importorskip("selectolax", reason="selectolax not installed")

from crawltop.core.table_extractor import ExtractedTable, TableExtractor, extract_tables


SIMPLE_HTML = """
<html><body>
<table>
  <tr><th>Team</th><th>W</th><th>L</th><th>PCT</th></tr>
  <tr><td>Yankees</td><td>92</td><td>70</td><td>.568</td></tr>
  <tr><td>Red Sox</td><td>78</td><td>84</td><td>.481</td></tr>
</table>
</body></html>
"""

CAPTION_HTML = """
<table>
  <caption>AL East Standings</caption>
  <tr><th>Team</th><th>GB</th></tr>
  <tr><td>Yankees</td><td>-</td></tr>
</table>
"""

EMPTY_HTML = "<html><body><p>No tables here</p></body></html>"

NARROW_HTML = """
<table>
  <tr><th>Col</th></tr>
  <tr><td>val</td></tr>
</table>
"""


class TestTableExtractor:
    def test_basic_extraction(self):
        tables = extract_tables(SIMPLE_HTML, source_url="http://example.com")
        assert len(tables) == 1
        t = tables[0]
        assert isinstance(t, ExtractedTable)
        assert t.headers == ["Team", "W", "L", "PCT"]
        assert len(t.rows) == 2
        assert t.rows[0]["Team"] == "Yankees"
        assert t.rows[0]["W"] == "92"
        assert t.source_url == "http://example.com"

    def test_caption(self):
        tables = extract_tables(CAPTION_HTML)
        assert len(tables) == 1
        assert tables[0].caption == "AL East Standings"

    def test_no_tables(self):
        tables = extract_tables(EMPTY_HTML)
        assert tables == []

    def test_min_cols_filter(self):
        """Table with only 1 column should be filtered out by default (min_cols=2)."""
        tables = extract_tables(NARROW_HTML)
        assert tables == []

    def test_min_cols_override(self):
        tables = extract_tables(NARROW_HTML, min_cols=1)
        assert len(tables) == 1

    def test_to_list(self):
        tables = extract_tables(SIMPLE_HTML)
        rows = tables[0].to_list()
        assert isinstance(rows, list)
        assert rows[0]["Team"] == "Yankees"

    def test_len(self):
        tables = extract_tables(SIMPLE_HTML)
        assert len(tables[0]) == 2

    def test_multiple_tables(self):
        html = SIMPLE_HTML + CAPTION_HTML
        tables = extract_tables(html)
        assert len(tables) == 2
        assert tables[0].table_index == 0
        assert tables[1].table_index == 1

    def test_cell_padding(self):
        """Rows with fewer cells than headers are padded with empty strings."""
        html = """
        <table>
          <tr><th>A</th><th>B</th><th>C</th></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>
        """
        tables = extract_tables(html)
        assert tables[0].rows[0]["C"] == ""

    def test_no_selectolax_raises(self, monkeypatch):
        import crawltop.core.table_extractor as te
        original = te.HTMLParser
        te.HTMLParser = None  # type: ignore
        try:
            with pytest.raises(RuntimeError, match="selectolax"):
                te.TableExtractor().extract("<html></html>")
        finally:
            te.HTMLParser = original
