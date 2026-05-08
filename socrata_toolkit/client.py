from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Generator

import pandas as pd
import requests

from .models import DatasetMetadata, SearchResult
from .utils import with_retries


@dataclass
class SocrataConfig:
    app_token: str | None = None
    timeout: int = 30
    page_size: int = 1000


class SocrataClient:
    def __init__(self, config: SocrataConfig | None = None) -> None:
        self.config = config or SocrataConfig(app_token=os.getenv("SOCRATA_APP_TOKEN"))

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
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

    def fetch_json(self, domain: str, fourfour: str, where: str | None = None, select: str | None = None, order: str | None = None, q: str | None = None, max_rows: int | None = None) -> Generator[list[dict[str, Any]], None, None]:
        offset = 0
        remaining = max_rows
        while True:
            limit = self.config.page_size if remaining is None else min(self.config.page_size, remaining)
            params: dict[str, Any] = {"$limit": limit, "$offset": offset}
            if where:
                params["$where"] = where
            if select:
                params["$select"] = select
            if order:
                params["$order"] = order
            if q:
                params["$q"] = q
            url = f"https://{domain}/resource/{fourfour}.json"
            resp = with_retries(lambda: requests.get(url, params=params, headers=self._headers(), timeout=self.config.timeout))
            batch = resp.json()
            if not batch:
                break
            yield batch
            got = len(batch)
            offset += got
            if remaining is not None:
                remaining -= got
                if remaining <= 0:
                    break

    def fetch_dataframe(self, domain: str, fourfour: str, **kwargs: Any) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for batch in self.fetch_json(domain, fourfour, **kwargs):
            rows.extend(batch)
        return pd.DataFrame(rows)

    def fetch_geojson(self, domain: str, fourfour: str, where: str | None = None, max_rows: int | None = None) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        offset = 0
        remaining = max_rows
        while True:
            limit = self.config.page_size if remaining is None else min(self.config.page_size, remaining)
            params: dict[str, Any] = {"$limit": limit, "$offset": offset}
            if where:
                params["$where"] = where
            url = f"https://{domain}/resource/{fourfour}.geojson"
            resp = with_retries(lambda: requests.get(url, params=params, headers=self._headers(), timeout=self.config.timeout))
            fc = resp.json()
            batch = fc.get("features", [])
            if not batch:
                break
            features.extend(batch)
            got = len(batch)
            offset += got
            if remaining is not None:
                remaining -= got
                if remaining <= 0:
                    break
        return {"type": "FeatureCollection", "features": features}
