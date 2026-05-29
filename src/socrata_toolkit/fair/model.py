"""Dataclasses modeling FAIR dataset metadata.

Implements the structural backbone for the FAIR Guiding Principles
(Wilkinson et al. 2016, Scientific Data 3:160018): metadata that is
Findable, Accessible, Interoperable, and Reusable.

Classes:
    SchemaField: A single column/field with type and semantics (Interoperable).
    FairDataset: Full FAIR metadata record for one dataset.
    FairnessScore: Result of scoring a dataset against the FAIR rubric.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SchemaField:
    """A single field in a dataset's schema (supports Interoperability).

    Attributes:
        name: Field/column name.
        datatype: Data type (e.g. ``string``, ``number``, ``date``).
        description: Human-readable description of the field.
        semantic_type: Optional vocabulary/ontology term (e.g. ``schema:GeoCoordinates``).
    """

    name: str
    datatype: str = ""
    description: str = ""
    semantic_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaField:
        return cls(**data)


@dataclass
class FairDataset:
    """FAIR metadata record for a dataset.

    Fields are grouped by FAIR principle:

    Findable:
        persistent_id, title, description, keywords, domain, fourfour.
    Accessible:
        landing_page, access_url, access_protocol, access_rights, license.
    Interoperable:
        format, conforms_to, vocabulary, schema_fields.
    Reusable:
        provenance, usage_rights, citation, license.
    """

    # --- Findable ---
    persistent_id: str = ""
    title: str = ""
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    domain: str = ""
    fourfour: str = ""

    # --- Accessible ---
    landing_page: str = ""
    access_url: str = ""
    access_protocol: str = ""
    access_rights: str = ""
    license: str = ""

    # --- Interoperable ---
    format: str = ""
    conforms_to: str = ""
    vocabulary: str = ""
    schema_fields: list[SchemaField] = field(default_factory=list)

    # --- Reusable ---
    provenance: dict[str, Any] = field(default_factory=dict)
    usage_rights: str = ""
    citation: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_fields"] = [f.to_dict() for f in self.schema_fields]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FairDataset:
        data = dict(data)
        raw_fields = data.get("schema_fields", []) or []
        data["schema_fields"] = [
            f if isinstance(f, SchemaField) else SchemaField.from_dict(f)
            for f in raw_fields
        ]
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class FairnessScore:
    """Outcome of scoring a dataset against the FAIR rubric.

    Each sub-score is in the range 0-25; ``overall`` is the sum normalized
    to 0-100 (here the sum is already 0-100 since 4 x 25 = 100).

    Attributes:
        overall: Total score, 0-100.
        findable: Findable sub-score, 0-25.
        accessible: Accessible sub-score, 0-25.
        interoperable: Interoperable sub-score, 0-25.
        reusable: Reusable sub-score, 0-25.
        gaps: Human-readable strings describing missing FAIR criteria.
    """

    overall: float = 0.0
    findable: float = 0.0
    accessible: float = 0.0
    interoperable: float = 0.0
    reusable: float = 0.0
    gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FairnessScore:
        return cls(**data)
