from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

import pandas as pd

from .spatial import _to_geom


@dataclass
class ConflictSummary:
    total_proposed: int
    total_conflicts: int
    conflict_rate: float


class ConflictResolver:
    """Resolve spatial conflicts between a proposed workset and reference layers.

    This is a lightweight, dependency-optional resolver that uses Shapely when available.
    Buffer distances are specified in meters and converted approximately to degrees.
    """

    def __init__(self):
        pass

    @staticmethod
    def _meters_to_degrees(meters: float, lat: float = 40.7128) -> float:
        # approximate conversion: 1 degree latitude ~= 111320 meters
        # adjust for longitude by cos(latitude) where needed; we use latitude of NYC by default
        return meters / (111320.0 * max(0.0001, math.cos(math.radians(lat))))

    def resolve_conflicts(self, proposed: pd.DataFrame, reference: pd.DataFrame, proposed_geom_col: str = "geometry", reference_geom_col: str = "geometry", buffer_m: float = 10.0) -> tuple[pd.DataFrame, ConflictSummary]:
        """Return proposed rows annotated with conflict info and a summary.

        proposed and reference may contain GeoJSON geometries or WKT strings in the given geometry columns.
        """
        try:
            from shapely.geometry import mapping
        except Exception as exc:
            raise ImportError("Install shapely to use ConflictResolver: pip install shapely") from exc

        left = proposed.copy()
        right = reference.copy()

        # convert to geometries
        left_geoms = left[proposed_geom_col].map(_to_geom)
        right_geoms = right[reference_geom_col].map(_to_geom)

        # estimate latitude for degree conversion
        sample_lat = None
        for g in left_geoms:
            if g is not None and hasattr(g, "centroid"):
                sample_lat = g.centroid.y
                break
        if sample_lat is None:
            sample_lat = 40.7128

        deg_buf = self._meters_to_degrees(buffer_m, sample_lat)

        conflict_flags = []
        conflict_counts = []
        conflict_lists = []

        r_items = list(right_geoms.items())

        for idx, lg in left_geoms.items():
            if lg is None:
                conflict_flags.append(False)
                conflict_counts.append(0)
                conflict_lists.append([])
                continue
            buf = lg.buffer(deg_buf)
            matches = []
            for ri, rg in r_items:
                if rg is None:
                    continue
                if buf.intersects(rg):
                    matches.append(int(ri))
            conflict_flags.append(bool(matches))
            conflict_counts.append(len(matches))
            conflict_lists.append(matches)

        left = left.reset_index(drop=True)
        left["_conflict"] = conflict_flags
        left["_conflict_count"] = conflict_counts
        left["_conflict_ids"] = conflict_lists

        total = len(left)
        total_conflicts = sum(1 for v in conflict_flags if v)
        summary = ConflictSummary(total_proposed=total, total_conflicts=total_conflicts, conflict_rate=(total_conflicts / total if total else 0.0))
        return left, summary

    def generate_construction_list(self, annotated: pd.DataFrame, priority_col: str | None = None, limit: int | None = None) -> pd.DataFrame:
        """Generate a prioritized construction list from the annotated proposed DataFrame.

        If `priority_col` exists it is used; otherwise rows with no conflicts are prioritized.
        """
        df = annotated.copy()
        if priority_col and priority_col in df.columns:
            df["_priority_score"] = df[priority_col].fillna(0)
        else:
            # prioritize non-conflicts first, then by _conflict_count desc
            df["_priority_score"] = df["_conflict"].apply(lambda x: 0 if not x else 1) + df["_conflict_count"].fillna(0)
        out = df.sort_values("_priority_score").reset_index(drop=True)
        if limit:
            out = out.head(limit)
        return out

    def export_geojson(self, df: pd.DataFrame, geom_col: str = "geometry") -> dict[str, Any]:
        """Return a GeoJSON FeatureCollection for the rows that have geometries."""
        try:
            from shapely.geometry import mapping
        except Exception as exc:
            raise ImportError("Install shapely to export GeoJSON: pip install shapely") from exc

        features = []
        for _, row in df.iterrows():
            geom = _to_geom(row.get(geom_col))
            props = {k: v for k, v in row.items() if k != geom_col}
            if geom is None:
                continue
            features.append({"type": "Feature", "geometry": mapping(geom), "properties": props})
        return {"type": "FeatureCollection", "features": features}


class PostGISConflictResolver:
    """Resolve spatial conflicts using a PostGIS-enabled PostgreSQL database.

    This resolver expects both the proposed and reference tables to already exist
    in PostGIS and to expose geometry columns (geometry or geography). The
    resolver returns a DataFrame with the original proposed table columns plus
    `_conflict_count` and `_conflict_ids` (array of text).
    """

    def __init__(self, dsn: str):
        try:
            import psycopg
        except Exception as exc:
            raise ImportError("Install Postgres extras: pip install '.[postgres]'") from exc
        self.psycopg = psycopg
        self.conn = psycopg.connect(dsn)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def _quote_ident(self, name: str) -> str:
        # Quote schema-qualified identifiers safely
        parts = [p.replace('"', '') for p in name.split('.')]
        return '.'.join(f'"{p}"' for p in parts)

    def resolve_conflicts(self, proposed_table: str, reference_table: str, proposed_id_col: str = "id", proposed_geom_col: str = "geom", reference_id_col: str = "id", reference_geom_col: str = "geom", buffer_m: float = 20.0) -> tuple[pd.DataFrame, ConflictSummary]:
        """Run a spatial join in PostGIS and return annotated proposed rows + summary.

        Parameters:
          - proposed_table, reference_table: table names (optionally schema-qualified)
          - *_id_col: identifier column name on each table used to join results
          - *_geom_col: geometry column name (must be PostGIS geometry/geography)
          - buffer_m: buffer (meters) for ST_DWithin
        """
        q_prop = self._quote_ident(proposed_table)
        q_ref = self._quote_ident(reference_table)
        pid = proposed_id_col.replace('"', '')
        rid = reference_id_col.replace('"', '')
        pgeom = proposed_geom_col.replace('"', '')
        rgeom = reference_geom_col.replace('"', '')

        sql = f"""
        WITH conflict_stats AS (
            SELECT p.{pid} AS proposed_id,
                   COUNT(r.{rid}) AS conflict_count,
                   ARRAY_AGG(r.{rid}::text) AS conflict_ids
            FROM {q_prop} p
            JOIN {q_ref} r
              ON ST_DWithin(p.{pgeom}::geography, r.{rgeom}::geography, %s)
            GROUP BY p.{pid}
        )
        SELECT p.*, COALESCE(s.conflict_count, 0) AS _conflict_count, COALESCE(s.conflict_ids, ARRAY[]::text[]) AS _conflict_ids
        FROM {q_prop} p
        LEFT JOIN conflict_stats s ON p.{pid} = s.proposed_id
        """

        cur = self.conn.cursor()
        cur.execute(sql, (buffer_m,))
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
        df = pd.DataFrame(rows, columns=cols)

        total = len(df)
        total_conflicts = int((df.get("_conflict_count", 0) > 0).sum()) if not df.empty else 0
        summary = ConflictSummary(total_proposed=total, total_conflicts=total_conflicts, conflict_rate=(total_conflicts / total if total else 0.0))
        return df, summary

