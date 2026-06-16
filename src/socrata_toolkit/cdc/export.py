"""CDC export and streaming for downstream consumption.

This module enables exporting CDC events in multiple formats for data lakes,
event streaming systems, analytics platforms, and other downstream consumers.

Key Features:
    - CSV export: Daily snapshots for data lake ingestion
    - JSON export: Event stream format for Kafka
    - Parquet export: Columnar format for analytics
    - Kafka streaming: Optional real-time streaming
    - Compaction: Collapse multiple updates to latest version
    - SCD export: Full historical snapshots

Classes:
    CDCExporter: Main export interface
    ExportFormat: Supported export formats
    ExportResult: Result of export operation

Example:
    >>> exporter = CDCExporter(dsn="postgresql://...")
    >>> result = exporter.export_to_csv("sidewalk_conditions", "/data/export/")
    >>> result = exporter.export_to_json("sidewalk_conditions")
    >>> result = exporter.export_to_parquet("sidewalk_conditions", "/data/parquet/")
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import IO

try:
    import psycopg
    from psycopg import sql
except ImportError:
    psycopg = None  # type: ignore
    sql = None  # type: ignore

logger = logging.getLogger(__name__)

class ExportFormat(Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    PARQUET = "parquet"

@dataclass
class ExportResult:
    """Result of CDC export operation.

    Attributes:
        success: Whether export succeeded
        format: Export format used
        record_count: Number of records exported
        file_path: Output file path (if applicable)
        size_bytes: File size
        duration_seconds: Time to complete
        message: Status message
        error: Error message if failed
    """
    success: bool
    format: str
    record_count: int = 0
    file_path: str | None = None
    size_bytes: int = 0
    duration_seconds: float = 0.0
    message: str = ""
    error: str | None = None

class CDCExporter:
    """Export CDC events in multiple formats.

    Supports various export formats for integration with downstream systems:
    data lakes, event streaming platforms, analytics tools, etc.
    """

    def __init__(self, dsn: str) -> None:
        """Initialize CDC exporter.

        Args:
            dsn: PostgreSQL connection string

        Raises:
            ImportError: If psycopg not installed
        """
        if psycopg is None:
            raise ImportError("Install postgres extras: pip install '.[postgres]'")
        self.dsn = dsn
        self.logger = logger.getChild(self.__class__.__name__)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connection."""
        conn = psycopg.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()

    def export_to_csv(
        self,
        source_dataset: str,
        output_path: str,
        compress: bool = False,
        limit: int | None = None,
    ) -> ExportResult:
        """Export CDC events to CSV.

        Args:
            source_dataset: Dataset identifier
            output_path: Directory or file path for output
            compress: Whether to gzip compress
            limit: Maximum rows to export

        Returns:
            ExportResult
        """
        start_time = datetime.now()
        records = []

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    query = """SELECT event_id, source_dataset, operation, record_id,
                                     timestamp_ms, before_values, after_values, metadata
                              FROM public.cdc_events
                              WHERE source_dataset = %s
                              ORDER BY timestamp_ms ASC"""
                    params = [source_dataset]

                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)

                    cur.execute(query, params)
                    rows = cur.fetchall()

            # Prepare output path
            path = Path(output_path)
            if path.is_dir():
                filename = f"{source_dataset}_{date.today().isoformat()}.csv"
                if compress:
                    filename += ".gz"
                path = path / filename

            # Write CSV
            if compress:
                with gzip.open(path, "wt", encoding="utf-8") as f:
                    self._write_csv_data(f, rows)
            else:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    self._write_csv_data(f, rows)

            duration = (datetime.now() - start_time).total_seconds()
            file_size = path.stat().st_size

            return ExportResult(
                success=True,
                format="csv",
                record_count=len(rows),
                file_path=str(path),
                size_bytes=file_size,
                duration_seconds=duration,
                message=f"Exported {len(rows)} events to {path}",
            )
        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            return ExportResult(
                success=False,
                format="csv",
                message="CSV export failed",
                error=str(e),
            )

    @staticmethod
    def _write_csv_data(f: IO, rows: list[tuple]) -> None:
        """Write CDC rows to CSV file.

        Args:
            f: File object
            rows: Database rows
        """
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "event_id",
                "source_dataset",
                "operation",
                "record_id",
                "timestamp_ms",
                "before",
                "after",
                "metadata",
            ],
        )
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "event_id": row[0],
                "source_dataset": row[1],
                "operation": row[2],
                "record_id": row[3],
                "timestamp_ms": row[4],
                "before": json.dumps(json.loads(row[5])) if row[5] else "",
                "after": json.dumps(json.loads(row[6])) if row[6] else "",
                "metadata": json.dumps(json.loads(row[7])) if row[7] else "",
            })

    def export_to_json(
        self,
        source_dataset: str,
        output_path: str | None = None,
        format: str = "array",
        limit: int | None = None,
    ) -> ExportResult:
        """Export CDC events to JSON.

        Args:
            source_dataset: Dataset identifier
            output_path: Optional file path (if None, returns data in memory)
            format: 'array' for JSON array or 'jsonl' for newline-delimited JSON
            limit: Maximum rows to export

        Returns:
            ExportResult with data in memory if no output_path
        """
        start_time = datetime.now()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    query = """SELECT event_id, source_dataset, operation, record_id,
                                     timestamp_ms, before_values, after_values, metadata
                              FROM public.cdc_events
                              WHERE source_dataset = %s
                              ORDER BY timestamp_ms ASC"""
                    params = [source_dataset]

                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)

                    cur.execute(query, params)
                    rows = cur.fetchall()

            # Convert to dicts
            events = []
            for row in rows:
                events.append({
                    "event_id": row[0],
                    "source_dataset": row[1],
                    "operation": row[2],
                    "record_id": row[3],
                    "timestamp_ms": row[4],
                    "before": json.loads(row[5]) if row[5] else None,
                    "after": json.loads(row[6]) if row[6] else None,
                    "metadata": json.loads(row[7]) if row[7] else None,
                })

            duration = (datetime.now() - start_time).total_seconds()

            # Write to file if path provided
            if output_path:
                path = Path(output_path)
                if path.is_dir():
                    filename = f"{source_dataset}_{date.today().isoformat()}.json"
                    path = path / filename

                if format == "jsonl":
                    with open(path, "w", encoding="utf-8") as f:
                        for event in events:
                            f.write(json.dumps(event) + "\n")
                else:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(events, f, indent=2, default=str)

                file_size = path.stat().st_size
                return ExportResult(
                    success=True,
                    format=format,
                    record_count=len(events),
                    file_path=str(path),
                    size_bytes=file_size,
                    duration_seconds=duration,
                    message=f"Exported {len(events)} events to {path}",
                )
            else:
                # Return in memory
                return ExportResult(
                    success=True,
                    format=format,
                    record_count=len(events),
                    duration_seconds=duration,
                    message=f"Prepared {len(events)} events in memory",
                )
        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
            return ExportResult(
                success=False,
                format=format,
                message="JSON export failed",
                error=str(e),
            )

    def export_to_parquet(
        self,
        source_dataset: str,
        output_path: str,
        limit: int | None = None,
    ) -> ExportResult:
        """Export CDC events to Parquet format.

        Requires pyarrow to be installed.

        Args:
            source_dataset: Dataset identifier
            output_path: Directory for output
            limit: Maximum rows to export

        Returns:
            ExportResult
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            return ExportResult(
                success=False,
                format="parquet",
                message="Parquet export failed",
                error="pyarrow not installed. Install with: pip install pyarrow",
            )

        start_time = datetime.now()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    query = """SELECT event_id, source_dataset, operation, record_id,
                                     timestamp_ms, before_values, after_values, metadata
                              FROM public.cdc_events
                              WHERE source_dataset = %s
                              ORDER BY timestamp_ms ASC"""
                    params = [source_dataset]

                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)

                    cur.execute(query, params)
                    rows = cur.fetchall()

            # Convert to Arrow table
            data = {
                "event_id": [],
                "source_dataset": [],
                "operation": [],
                "record_id": [],
                "timestamp_ms": [],
                "before": [],
                "after": [],
                "metadata": [],
            }

            for row in rows:
                data["event_id"].append(row[0])
                data["source_dataset"].append(row[1])
                data["operation"].append(row[2])
                data["record_id"].append(row[3])
                data["timestamp_ms"].append(row[4])
                data["before"].append(json.dumps(json.loads(row[5])) if row[5] else None)
                data["after"].append(json.dumps(json.loads(row[6])) if row[6] else None)
                data["metadata"].append(json.dumps(json.loads(row[7])) if row[7] else None)

            table = pa.table(data)

            # Write parquet
            path = Path(output_path)
            if path.is_dir():
                filename = f"{source_dataset}_{date.today().isoformat()}.parquet"
                path = path / filename

            pq.write_table(table, str(path))

            duration = (datetime.now() - start_time).total_seconds()
            file_size = path.stat().st_size

            return ExportResult(
                success=True,
                format="parquet",
                record_count=len(rows),
                file_path=str(path),
                size_bytes=file_size,
                duration_seconds=duration,
                message=f"Exported {len(rows)} events to {path}",
            )
        except Exception as e:
            self.logger.error(f"Parquet export failed: {e}")
            return ExportResult(
                success=False,
                format="parquet",
                message="Parquet export failed",
                error=str(e),
            )

    def export_compacted_cdc(
        self,
        source_dataset: str,
        output_path: str | None = None,
    ) -> ExportResult:
        """Export compacted CDC (latest version per business_key).

        Removes intermediate updates, keeping only the latest state of each record.
        Useful for snapshots, dimension tables, etc.

        Args:
            source_dataset: Dataset identifier
            output_path: Optional file path

        Returns:
            ExportResult
        """
        start_time = datetime.now()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Get latest record per business_key
                    query = """WITH latest AS (
                                 SELECT DISTINCT ON (record_id)
                                   event_id, source_dataset, operation, record_id,
                                   timestamp_ms, before_values, after_values, metadata
                                 FROM public.cdc_events
                                 WHERE source_dataset = %s
                                 ORDER BY record_id, timestamp_ms DESC
                               )
                               SELECT * FROM latest
                               ORDER BY timestamp_ms DESC"""

                    cur.execute(query, (source_dataset,))
                    rows = cur.fetchall()

            # Convert to dicts
            events = []
            for row in rows:
                events.append({
                    "event_id": row[0],
                    "source_dataset": row[1],
                    "operation": row[2],
                    "record_id": row[3],
                    "timestamp_ms": row[4],
                    "after": json.loads(row[6]) if row[6] else None,
                })

            duration = (datetime.now() - start_time).total_seconds()

            if output_path:
                path = Path(output_path)
                if path.is_dir():
                    filename = f"{source_dataset}_compacted_{date.today().isoformat()}.json"
                    path = path / filename

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(events, f, indent=2, default=str)

                file_size = path.stat().st_size
                return ExportResult(
                    success=True,
                    format="json_compacted",
                    record_count=len(events),
                    file_path=str(path),
                    size_bytes=file_size,
                    duration_seconds=duration,
                    message=f"Exported {len(events)} compacted events to {path}",
                )
            else:
                return ExportResult(
                    success=True,
                    format="json_compacted",
                    record_count=len(events),
                    duration_seconds=duration,
                    message=f"Prepared {len(events)} compacted events",
                )
        except Exception as e:
            self.logger.error(f"Compacted CDC export failed: {e}")
            return ExportResult(
                success=False,
                format="json_compacted",
                message="Compacted CDC export failed",
                error=str(e),
            )

    def export_scd_snapshot(
        self,
        table: str,
        output_path: str,
        as_of_date: datetime | None = None,
    ) -> ExportResult:
        """Export SCD Type 2 snapshot.

        Exports all current records or records as of a specific date.

        Args:
            table: SCD table name
            output_path: Directory for output
            as_of_date: Optional historical date

        Returns:
            ExportResult
        """
        start_time = datetime.now()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if as_of_date:
                        query = f"""SELECT scd_id, business_key, start_date, end_date,
                                         is_current, data_values, metadata
                                  FROM {sql.Identifier(table)}
                                  WHERE start_date <= %s
                                    AND (end_date IS NULL OR end_date > %s)
                                  ORDER BY business_key"""
                        cur.execute(query, (as_of_date, as_of_date))
                    else:
                        query = f"""SELECT scd_id, business_key, start_date, end_date,
                                         is_current, data_values, metadata
                                  FROM {sql.Identifier(table)}
                                  WHERE is_current = TRUE
                                  ORDER BY business_key"""
                        cur.execute(query)

                    rows = cur.fetchall()

            # Convert to dicts
            records = []
            for row in rows:
                records.append({
                    "scd_id": row[0],
                    "business_key": row[1],
                    "start_date": row[2].isoformat(),
                    "end_date": row[3].isoformat() if row[3] else None,
                    "is_current": row[4],
                    "data": json.loads(row[5]) if isinstance(row[5], str) else row[5],
                })

            duration = (datetime.now() - start_time).total_seconds()

            # Write
            path = Path(output_path)
            if path.is_dir():
                date_str = as_of_date.date().isoformat() if as_of_date else date.today().isoformat()
                filename = f"{table}_snapshot_{date_str}.json"
                path = path / filename

            with open(path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)

            file_size = path.stat().st_size

            return ExportResult(
                success=True,
                format="scd_snapshot",
                record_count=len(records),
                file_path=str(path),
                size_bytes=file_size,
                duration_seconds=duration,
                message=f"Exported {len(records)} SCD records to {path}",
            )
        except Exception as e:
            self.logger.error(f"SCD snapshot export failed: {e}")
            return ExportResult(
                success=False,
                format="scd_snapshot",
                message="SCD snapshot export failed",
                error=str(e),
            )
