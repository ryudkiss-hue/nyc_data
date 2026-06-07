"""Socrata API client utilities.

This module provides a small, resilient HTTP client for the Socrata SODA API
with convenience methods for streaming JSON pages, converting to a pandas
DataFrame, and fetching GeoJSON features. Methods are intentionally
memory-conscious: `fetch_json` yields pages (lists) of dicts instead of
loading the entire dataset into memory.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from .models import DatasetMetadata, SearchResult
from .utils import with_retries


@dataclass
class SocrataConfig:
    app_token: str | None = None
    timeout: int = 30
    page_size: int = 1000
    soda_version: str = "3.0" # Default to SODA3


class SocrataClient:
    def __init__(self, config: SocrataConfig | None = None) -> None:
        self.config = config or SocrataConfig(app_token=os.getenv("SOCRATA_APP_TOKEN"))

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.app_token:
            h["X-App-Token"] = self.config.app_token
        return h

    def search(
        self,
        query: str | None = None,
        domain: str | None = None,
        category: str | None = None,
        tags: str | None = None,
        order: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if domain:
            params["domains"] = domain
        if category:
            params["categories"] = category
        if tags:
            params["tags"] = tags
        if order:
            params["order"] = order
        resp = with_retries(lambda: requests.get("https://api.us.socrata.com/api/catalog/v1", params=params, headers=self._headers(), timeout=self.config.timeout))
        resp.raise_for_status()
        results = []
        for item in resp.json().get("results", []):
            resource = item.get("resource", {})
            results.append(
                SearchResult(
                    name=resource.get("name", ""),
                    description=resource.get("description", ""),
                    domain=item.get("metadata", {}).get("domain", ""),
                    fourfour=resource.get("id", ""),
                    page_views_last_month=resource.get("page_views", {}).get("page_views_last_month"),
                    category=resource.get("category"),
                    tags=resource.get("tags", []),
                )
            )
        return results

    def get_metadata(self, domain: str, fourfour: str) -> DatasetMetadata:
        url = f"https://{domain}/api/views/{fourfour}.json"
        resp = with_retries(lambda: requests.get(url, headers=self._headers(), timeout=self.config.timeout))
        resp.raise_for_status()
        payload = resp.json()
        return DatasetMetadata(
            domain=domain,
            fourfour=fourfour,
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            row_count=payload.get("rowsCount") or payload.get("viewCount"),
            license=(payload.get("license") or {}).get("name") if isinstance(payload.get("license"), dict) else None,
            columns=payload.get("columns", []),
        )

    def _build_soql(
        self,
        limit: int,
        offset: int,
        select: str | None = None,
        where: str | None = None,
        order: str | None = None,
    ) -> str:
        """Build a SoQL SELECT statement for SODA3."""
        parts: list[str] = []
        parts.append(f"SELECT {select}" if select else "SELECT *")
        if where:
            parts.append(f"WHERE {where}")
        if order:
            parts.append(f"ORDER BY {order}")
        parts.append(f"LIMIT {limit}")
        parts.append(f"OFFSET {offset}")
        return " ".join(parts)

    def fetch_json(self, domain: str, fourfour: str, where: str | None = None, select: str | None = None, order: str | None = None, max_rows: int | str | None = None, version: str | None = None) -> Generator[list[dict[str, Any]], None, None]:
        """Stream JSON pages via the SODA3 POST endpoint or SODA2 GET fallback."""
        v = version or self.config.soda_version
        
        # Strictly cast max_rows to int if it's a string
        if max_rows is not None:
            try:
                max_rows = int(max_rows)
            except ValueError:
                max_rows = None

        if v.startswith("2") or not self.config.app_token:
            if not self.config.app_token and v.startswith("3"):
                import warnings as _warnings
                _warnings.warn("SODA3 requires authentication; falling back to SODA2.", stacklevel=2)
            yield from self._fetch_json_soda2(domain, fourfour, where=where, select=select, order=order, max_rows=max_rows)
            return

        # SODA3 POST path
        offset = 0
        remaining = max_rows
        url = f"https://{domain}/api/v3/views/{fourfour}/query.json"
        
        while True:
            limit = self.config.page_size if remaining is None else min(self.config.page_size, remaining)
            soql = self._build_soql(limit, offset, select=select, where=where, order=order)
            payload = {
                "query": soql,
                "options": {"orderingSpecifier": "preserve" if order else "discard"}
            }
            resp = with_retries(lambda: requests.post(url, json=payload, headers=self._headers(), timeout=self.config.timeout))
            resp.raise_for_status()
            batch = resp.json()
            if not batch: break
            yield batch
            got = len(batch)
            offset += got
            if remaining is not None:
                remaining -= got
                if remaining <= 0: break

    def _fetch_json_soda2(self, domain: str, fourfour: str, where: str | None = None, select: str | None = None, order: str | None = None, max_rows: int | str | None = None) -> Generator[list[dict[str, Any]], None, None]:
        """SODA2 GET fallback."""
        offset = 0
        remaining = int(max_rows) if max_rows is not None else None
        while True:
            limit = self.config.page_size if remaining is None else min(self.config.page_size, remaining)
            params: dict[str, Any] = {"$limit": limit, "$offset": offset}
            if where: params["$where"] = where
            if select: params["$select"] = select
            if order: params["$order"] = order
            url = f"https://{domain}/resource/{fourfour}.json"
            resp = with_retries(lambda: requests.get(url, params=params, headers=self._headers(), timeout=self.config.timeout))
            resp.raise_for_status()
            batch = resp.json()
            if not batch: break
            yield batch
            got = len(batch)
            offset += got
            if remaining is not None:
                remaining -= got
                if remaining <= 0: break

    def fetch_dataframe(self, domain: str, fourfour: str, **kwargs: Any) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for batch in self.fetch_json(domain, fourfour, **kwargs):
            rows.extend(batch)
        return pd.DataFrame(rows)

    def fetch_geojson(self, domain: str, fourfour: str, where: str | None = None, max_rows: int | str | None = None, version: str | None = None) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        offset = 0
        remaining = int(max_rows) if max_rows is not None else None
        v = version or self.config.soda_version

        if v.startswith("3") and self.config.app_token:
            url = f"https://{domain}/api/v3/views/{fourfour}/query.geojson"
            while True:
                limit = self.config.page_size if remaining is None else min(self.config.page_size, remaining)
                soql = self._build_soql(limit, offset, where=where)
                resp = with_retries(lambda: requests.post(url, json={"query": soql}, headers=self._headers(), timeout=self.config.timeout))
                resp.raise_for_status()
                fc = resp.json()
                batch = fc.get("features", [])
                if not batch: break
                features.extend(batch)
                got = len(batch)
                offset += got
                if remaining is not None:
                    remaining -= got
                    if remaining <= 0: break
        else:
            while True:
                limit = self.config.page_size if remaining is None else min(self.config.page_size, remaining)
                params: dict[str, Any] = {"$limit": limit, "$offset": offset}
                if where: params["$where"] = where
                url_soda2 = f"https://{domain}/resource/{fourfour}.geojson"
                resp = with_retries(lambda: requests.get(url_soda2, params=params, headers=self._headers(), timeout=self.config.timeout))
                resp.raise_for_status()
                fc = resp.json()
                batch = fc.get("features", [])
                if not batch: break
                features.extend(batch)
                got = len(batch)
                offset += got
                if remaining is not None:
                    remaining -= got
                    if remaining <= 0: break
        return {"type": "FeatureCollection", "features": features}

    def fetch_since(self, domain: str, fourfour: str, updated_col: str, since: str, **kwargs: Any) -> Generator[list[dict[str, Any]], None, None]:
        where = kwargs.pop("where", None)
        escaped_since = since.replace("'", "''")
        clause = f"{updated_col} > '{escaped_since}'"
        if where: where = f"({where}) AND ({clause})"
        else: where = clause
        yield from self.fetch_json(domain, fourfour, where=where, **kwargs)
