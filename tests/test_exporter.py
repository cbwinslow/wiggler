"""tests/test_exporter.py - unit tests for crawltop/pipeline/exporter.py."""
import csv
import json
import sqlite3
from pathlib import Path

import pytest

from crawltop.db.schema import ensure_schema
from crawltop.pipeline.exporter import Exporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_db(tmp_path):
    """Temp SQLite DB with schema applied and one run + two pages."""
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(db_path)
    ensure_schema(con)
    # Insert a run
    con.execute(
        "INSERT INTO runs(id, seed_url, status) VALUES (1,'https://mlb.com','done')"
    )
    # Insert two pages
    con.execute(
        """
        INSERT INTO pages(id, run_id, url, status_code, title, depth)
        VALUES (1, 1, 'https://mlb.com', 200, 'MLB Home', 0)
        """
    )
    con.execute(
        """
        INSERT INTO pages(id, run_id, url, status_code, title, depth)
        VALUES (2, 1, 'https://mlb.com/standings', 200, 'Standings', 1)
        """
    )
    con.commit()
    con.close()
    return db_path


@pytest.fixture
def exporter(tmp_db):
    return Exporter(tmp_db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestExporterJSON:
    def test_json_output(self, exporter, tmp_path):
        dest = tmp_path / "out.json"
        result = exporter.export(1, fmt="json", dest=dest)
        assert result == dest
        data = json.loads(dest.read_text())
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["url"] == "https://mlb.com"

    def test_jsonl_output(self, exporter, tmp_path):
        dest = tmp_path / "out.jsonl"
        result = exporter.export(1, fmt="jsonl", dest=dest)
        lines = dest.read_text().strip().splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["title"] == "MLB Home"

    def test_csv_output(self, exporter, tmp_path):
        dest = tmp_path / "out.csv"
        exporter.export(1, fmt="csv", dest=dest)
        with dest.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[1]["title"] == "Standings"

    def test_markdown_output(self, exporter, tmp_path):
        dest = tmp_path / "out.md"
        exporter.export(1, fmt="markdown", dest=dest)
        content = dest.read_text()
        assert "| url |" in content or "url" in content
        assert "mlb.com" in content

    def test_unknown_format_raises(self, exporter, tmp_path):
        with pytest.raises(ValueError, match="Unknown format"):
            exporter.export(1, fmt="xml", dest=tmp_path / "out.xml")  # type: ignore

    def test_default_dest_generated(self, exporter, tmp_path, monkeypatch):
        """When dest=None a default path is created in the cwd."""
        monkeypatch.chdir(tmp_path)
        result = exporter.export(1, fmt="jsonl")
        assert result.exists()
        assert result.name == "run_1.jsonl"
        result.unlink()

    def test_empty_run(self, exporter, tmp_path):
        """Exporting a run with no pages returns an empty list/file."""
        dest = tmp_path / "empty.json"
        exporter.export(99, fmt="json", dest=dest)  # run 99 doesn't exist
        data = json.loads(dest.read_text())
        assert data == []

    def test_parquet_missing_dep(self, exporter, tmp_path, monkeypatch):
        """Parquet export raises RuntimeError when pyarrow not installed."""
        import sys
        # Remove pyarrow from sys.modules if present so the import inside fails
        pyarrow_mod = sys.modules.pop("pyarrow", None)
        try:
            with pytest.raises((RuntimeError, ImportError)):
                exporter.export(1, fmt="parquet", dest=tmp_path / "out.parquet")
        finally:
            if pyarrow_mod is not None:
                sys.modules["pyarrow"] = pyarrow_mod
