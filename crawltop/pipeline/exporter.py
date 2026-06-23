"""crawltop/pipeline/exporter.py

Advanced multi-format exporter for crawltop run data (v0.5).

Supported formats
-----------------
json    - Pretty-printed JSON array of page records
jsonl   - One JSON object per line (streaming-friendly)
csv     - Flat CSV of page records
markdown - Human-readable Markdown table summary

Optional (requires pyarrow)
parquet - Columnar Parquet file

Usage
-----
    from crawltop.pipeline.exporter import Exporter
    exp = Exporter(db_path="crawltop.db")
    exp.export(run_id=1, fmt="jsonl", dest="out/run1.jsonl")
"""
from __future__ import annotations

import csv
import io
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Iterator, Literal, Optional, Union

log = logging.getLogger(__name__)

FMT = Literal["json", "jsonl", "csv", "markdown", "parquet"]

# Columns exported from the pages table
_PAGE_COLS = (
    "id", "run_id", "url", "fetched_at", "status_code",
    "content_type", "title", "depth",
)


class Exporter:
    """Export crawl run data to various file formats.

    Parameters
    ----------
    db_path:
        Path to the crawltop SQLite database file.
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = Path(db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def export(
        self,
        run_id: int,
        fmt: FMT = "jsonl",
        dest: Optional[Union[str, Path]] = None,
        include_tables: bool = False,
        include_entities: bool = False,
    ) -> Path:
        """Export run *run_id* in format *fmt* to *dest*.

        If *dest* is None a default filename is generated in the current
        directory.  Returns the output path.
        """
        if dest is None:
            dest = Path(f"run_{run_id}.{fmt}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)

        records = list(
            self._iter_pages(run_id, include_tables, include_entities)
        )
        log.info(
            "Exporting run %d (%d pages) -> %s [%s]",
            run_id, len(records), dest, fmt,
        )

        writers = {
            "json":     self._write_json,
            "jsonl":    self._write_jsonl,
            "csv":      self._write_csv,
            "markdown": self._write_markdown,
            "parquet":  self._write_parquet,
        }
        if fmt not in writers:
            raise ValueError(f"Unknown format {fmt!r}. Choose: {list(writers)}")
        writers[fmt](records, dest)
        log.info("Export complete: %s", dest)
        return dest

    def export_extracted_tables(
        self,
        run_id: int,
        dest: Optional[Union[str, Path]] = None,
        fmt: FMT = "jsonl",
    ) -> Path:
        """Export extracted HTML tables for an entire run."""
        if dest is None:
            dest = Path(f"run_{run_id}_tables.{fmt}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        records = list(self._iter_extracted_tables(run_id))
        log.info(
            "Exporting %d extracted tables -> %s", len(records), dest
        )
        writers = {
            "json": self._write_json,
            "jsonl": self._write_jsonl,
        }
        writers.get(fmt, self._write_jsonl)(records, dest)
        return dest

    # ------------------------------------------------------------------
    # DB iterators
    # ------------------------------------------------------------------
    def _iter_pages(
        self,
        run_id: int,
        include_tables: bool,
        include_entities: bool,
    ) -> Iterator[dict[str, Any]]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            cols = ", ".join(f"p.{c}" for c in _PAGE_COLS)
            rows = con.execute(
                f"SELECT {cols} FROM pages p WHERE p.run_id = ? ORDER BY p.id",
                (run_id,),
            ).fetchall()
            for row in rows:
                rec: dict[str, Any] = dict(row)
                if include_tables:
                    rec["extracted_tables"] = self._page_tables(
                        con, rec["id"]
                    )
                if include_entities:
                    rec["entity_links"] = self._page_entities(
                        con, rec["id"]
                    )
                yield rec
        finally:
            con.close()

    def _iter_extracted_tables(
        self, run_id: int
    ) -> Iterator[dict[str, Any]]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                """
                SELECT et.*, p.url
                FROM extracted_tables et
                JOIN pages p ON p.id = et.page_id
                WHERE p.run_id = ?
                ORDER BY et.page_id, et.table_index
                """,
                (run_id,),
            ).fetchall()
            for row in rows:
                rec = dict(row)
                # Parse JSON cols back to Python
                rec["headers"] = json.loads(rec.pop("headers_json", "[]"))
                rec["rows"] = json.loads(rec.pop("rows_json", "[]"))
                yield rec
        finally:
            con.close()

    @staticmethod
    def _page_tables(
        con: sqlite3.Connection, page_id: int
    ) -> list[dict[str, Any]]:
        rows = con.execute(
            "SELECT * FROM extracted_tables WHERE page_id = ? ORDER BY table_index",
            (page_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["headers"] = json.loads(d.pop("headers_json", "[]"))
            d["rows"] = json.loads(d.pop("rows_json", "[]"))
            result.append(d)
        return result

    @staticmethod
    def _page_entities(
        con: sqlite3.Connection, page_id: int
    ) -> list[dict[str, Any]]:
        rows = con.execute(
            "SELECT * FROM entity_links WHERE page_id = ?",
            (page_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------
    @staticmethod
    def _write_json(records: list[dict], dest: Path) -> None:
        dest.write_text(
            json.dumps(records, indent=2, default=str), encoding="utf-8"
        )

    @staticmethod
    def _write_jsonl(records: list[dict], dest: Path) -> None:
        with dest.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, default=str) + "\n")

    @staticmethod
    def _write_csv(records: list[dict], dest: Path) -> None:
        if not records:
            dest.write_text("", encoding="utf-8")
            return
        # Flatten nested structures for CSV
        flat = []
        for rec in records:
            flat.append(
                {k: v for k, v in rec.items() if not isinstance(v, (dict, list))}
            )
        fieldnames = list(flat[0].keys()) if flat else []
        with dest.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(flat)

    @staticmethod
    def _write_markdown(records: list[dict], dest: Path) -> None:
        if not records:
            dest.write_text("*(no records)*\n", encoding="utf-8")
            return
        # Simple table using top-level scalar fields
        scalar_keys = [
            k for k, v in records[0].items()
            if not isinstance(v, (dict, list))
        ]
        lines = [
            "| " + " | ".join(scalar_keys) + " |",
            "| " + " | ".join("---" for _ in scalar_keys) + " |",
        ]
        for rec in records:
            row = [str(rec.get(k, "")) for k in scalar_keys]
            lines.append("| " + " | ".join(row) + " |")
        dest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _write_parquet(records: list[dict], dest: Path) -> None:
        try:
            import pyarrow as pa  # type: ignore
            import pyarrow.parquet as pq  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "pyarrow is required for Parquet export: pip install pyarrow"
            ) from exc
        # Flatten nested structures
        flat = [
            {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
             for k, v in rec.items()}
            for rec in records
        ]
        table = pa.Table.from_pylist(flat)
        pq.write_table(table, dest)


# ---------------------------------------------------------------------------
# CLI helper (python -m crawltop.pipeline.exporter)
# ---------------------------------------------------------------------------
def _cli() -> None:  # pragma: no cover
    import argparse
    parser = argparse.ArgumentParser(description="Export a crawltop run")
    parser.add_argument("db", help="Path to crawltop.db")
    parser.add_argument("run_id", type=int, help="Run ID to export")
    parser.add_argument(
        "--fmt", default="jsonl",
        choices=["json", "jsonl", "csv", "markdown", "parquet"],
        help="Output format (default: jsonl)",
    )
    parser.add_argument("--dest", help="Output file path")
    parser.add_argument(
        "--tables", action="store_true", help="Include extracted HTML tables"
    )
    parser.add_argument(
        "--entities", action="store_true", help="Include entity links"
    )
    args = parser.parse_args()
    exp = Exporter(args.db)
    out = exp.export(
        args.run_id,
        fmt=args.fmt,
        dest=args.dest,
        include_tables=args.tables,
        include_entities=args.entities,
    )
    print(f"Exported to {out}")


if __name__ == "__main__":  # pragma: no cover
    _cli()
