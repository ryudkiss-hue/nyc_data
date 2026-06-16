"""FAIR metadata catalog with DCAT JSON-LD export.

Provides :class:`FairCatalog`, an in-memory collection of
:class:`FairDataset` records with JSON persistence, bulk FAIR scoring,
and export to a DCAT-compliant JSON-LD catalog.
"""

from __future__ import annotations

import json
from typing import Any

from .model import FairDataset, FairnessScore
from .scoring import score_fairness

# Standard vocabulary namespaces for the JSON-LD @context.
_DCAT_CONTEXT = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "schema": "http://schema.org/",
    "foaf": "http://xmlns.com/foaf/0.1/",
}

class FairCatalog:
    """A catalog of FAIR dataset metadata records.

    Datasets are keyed by a catalog id (the caller-supplied id, falling
    back to ``persistent_id`` then ``fourfour``).
    """

    def __init__(self, title: str = "FAIR Dataset Catalog") -> None:
        self.title = title
        self._datasets: dict[str, FairDataset] = {}

    # --- CRUD ---
    def add(self, dataset: FairDataset, dataset_id: str | None = None) -> str:
        """Add a dataset and return its catalog id."""
        ds_id = dataset_id or dataset.persistent_id or dataset.fourfour
        if not ds_id:
            raise ValueError("dataset needs an id, persistent_id, or fourfour")
        self._datasets[ds_id] = dataset
        return ds_id

    def get(self, dataset_id: str) -> FairDataset | None:
        return self._datasets.get(dataset_id)

    def list(self) -> list[str]:
        """Return the catalog ids of all datasets."""
        return list(self._datasets.keys())

    def __len__(self) -> int:
        return len(self._datasets)

    # --- Scoring ---
    def score_all(self) -> dict[str, FairnessScore]:
        """Score every dataset, returning ``{catalog_id: FairnessScore}``."""
        return {ds_id: score_fairness(ds) for ds_id, ds in self._datasets.items()}

    # --- JSON persistence ---
    def to_json(self, *, indent: int | None = 2) -> str:
        payload = {
            "title": self.title,
            "datasets": {k: v.to_dict() for k, v in self._datasets.items()},
        }
        return json.dumps(payload, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> FairCatalog:
        payload = json.loads(text)
        catalog = cls(title=payload.get("title", "FAIR Dataset Catalog"))
        for ds_id, data in payload.get("datasets", {}).items():
            catalog.add(FairDataset.from_dict(data), dataset_id=ds_id)
        return catalog

    # --- DCAT JSON-LD export ---
    def to_dcat_jsonld(self) -> dict[str, Any]:
        """Export the catalog as a DCAT-style JSON-LD document.

        Produces a ``dcat:Catalog`` whose ``dcat:dataset`` array holds
        ``dcat:Dataset`` nodes using dct/dcat/schema.org terms. The result
        is self-describing via ``@context`` and JSON-serializable.
        """
        datasets = [self._dataset_node(ds_id, ds) for ds_id, ds in self._datasets.items()]
        return {
            "@context": _DCAT_CONTEXT,
            "@type": "dcat:Catalog",
            "dct:title": self.title,
            "dcat:dataset": datasets,
        }

    @staticmethod
    def _dataset_node(ds_id: str, ds: FairDataset) -> dict[str, Any]:
        node: dict[str, Any] = {
            "@id": ds.persistent_id or ds_id,
            "@type": "dcat:Dataset",
            "dct:identifier": ds.persistent_id or ds_id,
            "dct:title": ds.title,
            "dct:description": ds.description,
            "dcat:keyword": list(ds.keywords),
            "dcat:theme": ds.domain,
            "dct:license": ds.license,
            "dct:rights": ds.usage_rights or ds.access_rights,
            "dct:conformsTo": ds.conforms_to,
            "dcat:landingPage": ds.landing_page,
            "dct:provenance": ds.provenance,
            "schema:citation": ds.citation,
        }
        if ds.access_url:
            node["dcat:distribution"] = {
                "@type": "dcat:Distribution",
                "dcat:accessURL": ds.access_url,
                "dct:format": ds.format,
                "dcat:accessService": ds.access_protocol,
            }
        if ds.schema_fields:
            node["dcat:schema"] = [
                {
                    "@type": "schema:PropertyValue",
                    "schema:name": f.name,
                    "schema:valueRequired": False,
                    "dct:type": f.datatype,
                    "dct:description": f.description,
                    "schema:additionalType": f.semantic_type,
                }
                for f in ds.schema_fields
            ]
        return node
