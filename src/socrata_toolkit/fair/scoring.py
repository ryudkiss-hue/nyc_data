"""Transparent FAIR scoring rubric.

Scores a :class:`FairDataset` against the four FAIR principles, awarding
0-25 points per principle from concrete, documented checks. The overall
score is the sum (0-100). Every failed check appends a human-readable
string to ``FairnessScore.gaps`` so results are auditable.
"""

from __future__ import annotations

from .model import FairDataset, FairnessScore

_RICH_DESCRIPTION_CHARS = 50
_MIN_KEYWORDS = 3

def _findable(ds: FairDataset, gaps: list[str]) -> float:
    """Findable: metadata is discoverable and uniquely identified.

    Checks (each worth points up to 25 total):
        +7  has a persistent identifier
        +6  has >= 3 keywords for indexing
        +6  has a rich description (>= 50 chars)
        +6  has a domain/topic set (aids categorization/indexing)
    """
    score = 0.0
    if ds.persistent_id.strip():
        score += 7
    else:
        gaps.append("Findable: missing persistent_id")
    if len([k for k in ds.keywords if k.strip()]) >= _MIN_KEYWORDS:
        score += 6
    else:
        gaps.append(f"Findable: fewer than {_MIN_KEYWORDS} keywords")
    if len(ds.description.strip()) >= _RICH_DESCRIPTION_CHARS:
        score += 6
    else:
        gaps.append("Findable: description missing or too short for indexing")
    if ds.domain.strip():
        score += 6
    else:
        gaps.append("Findable: no domain/topic set")
    return score

def _accessible(ds: FairDataset, gaps: list[str]) -> float:
    """Accessible: data is retrievable via a standard, open protocol.

    Checks:
        +7  has an access_url (machine-retrievable endpoint)
        +6  declares an access_protocol (e.g. HTTPS, SODA, OAI-PMH)
        +6  states access_rights (open / restricted)
        +6  has a landing_page for human access
    """
    score = 0.0
    if ds.access_url.strip():
        score += 7
    else:
        gaps.append("Accessible: missing access_url")
    if ds.access_protocol.strip():
        score += 6
    else:
        gaps.append("Accessible: no access_protocol declared")
    if ds.access_rights.strip():
        score += 6
    else:
        gaps.append("Accessible: access_rights not stated")
    if ds.landing_page.strip():
        score += 6
    else:
        gaps.append("Accessible: no landing_page")
    return score

def _interoperable(ds: FairDataset, gaps: list[str]) -> float:
    """Interoperable: uses standard formats and shared vocabularies.

    Checks:
        +7  declares a machine-readable format (e.g. CSV, JSON, GeoJSON)
        +6  references a vocabulary/ontology
        +6  conforms_to a known standard/schema
        +6  schema_fields documented with datatypes
    """
    score = 0.0
    if ds.format.strip():
        score += 7
    else:
        gaps.append("Interoperable: no format declared")
    if ds.vocabulary.strip():
        score += 6
    else:
        gaps.append("Interoperable: no controlled vocabulary referenced")
    if ds.conforms_to.strip():
        score += 6
    else:
        gaps.append("Interoperable: no conformance standard (conforms_to)")
    if ds.schema_fields and all(f.datatype.strip() for f in ds.schema_fields):
        score += 6
    else:
        gaps.append("Interoperable: schema_fields missing or untyped")
    return score

def _reusable(ds: FairDataset, gaps: list[str]) -> float:
    """Reusable: clear license, provenance, and usage guidance.

    Checks:
        +7  has a license
        +6  has provenance (source, publisher, issued/modified)
        +6  states usage_rights
        +6  provides a citation
    """
    score = 0.0
    if ds.license.strip():
        score += 7
    else:
        gaps.append("Reusable: no license")
    if ds.provenance and any(str(v).strip() for v in ds.provenance.values()):
        score += 6
    else:
        gaps.append("Reusable: provenance not documented")
    if ds.usage_rights.strip():
        score += 6
    else:
        gaps.append("Reusable: usage_rights not stated")
    if ds.citation.strip():
        score += 6
    else:
        gaps.append("Reusable: no citation provided")
    return score

def score_fairness(ds: FairDataset) -> FairnessScore:
    """Score a dataset against the FAIR rubric.

    Returns a :class:`FairnessScore` with four 0-25 sub-scores, an
    overall 0-100 total (their sum), and a list of human-readable gaps
    for every unmet criterion.
    """
    gaps: list[str] = []
    findable = _findable(ds, gaps)
    accessible = _accessible(ds, gaps)
    interoperable = _interoperable(ds, gaps)
    reusable = _reusable(ds, gaps)
    overall = findable + accessible + interoperable + reusable
    return FairnessScore(
        overall=round(overall, 2),
        findable=findable,
        accessible=accessible,
        interoperable=interoperable,
        reusable=reusable,
        gaps=gaps,
    )
