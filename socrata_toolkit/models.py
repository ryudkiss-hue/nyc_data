from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    name: str
    description: str
    domain: str
    fourfour: str
    page_views_last_month: int | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class DatasetMetadata:
    domain: str
    fourfour: str
    name: str
    description: str
    row_count: int | None
    license: str | None
    columns: list[dict[str, Any]]

    @property
    def is_geo(self) -> bool:
        geo_types = {"point", "polygon", "line", "multipolygon", "location"}
        for c in self.columns:
            ctype = str(c.get("dataTypeName", "")).lower()
            if ctype in geo_types or "location" in ctype:
                return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "fourfour": self.fourfour,
            "name": self.name,
            "description": self.description,
            "row_count": self.row_count,
            "license": self.license,
            "is_geo": self.is_geo,
        }

    def column_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "name": c.get("name"),
                "fieldName": c.get("fieldName"),
                "dataTypeName": c.get("dataTypeName"),
                "description": c.get("description"),
                "position": c.get("position"),
            }
            for c in self.columns
        ]
