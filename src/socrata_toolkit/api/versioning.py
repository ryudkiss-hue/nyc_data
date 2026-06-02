from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VersionStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


@dataclass
class APIVersion:
    version: str
    status: VersionStatus = VersionStatus.ACTIVE
    breaking_changes: list[str] = field(default_factory=list)
    deprecation_date: datetime | None = None
    sunset_date: datetime | None = None

    def is_deprecated(self) -> bool:
        return self.status == VersionStatus.DEPRECATED


@dataclass
class NegotiationResult:
    negotiated_version: str


class VersionManager:
    def __init__(self):
        self.versions: dict[str, APIVersion] = {}

    def register_version(self, version: str, status: VersionStatus = VersionStatus.ACTIVE, breaking_changes: list[str] | None = None):
        self.versions[version] = APIVersion(version=version, status=status, breaking_changes=breaking_changes or [])

    def get_version(self, version: str) -> APIVersion | None:
        return self.versions.get(version)

    def negotiate_version(self, request_version: str | None = None) -> NegotiationResult:
        if request_version and request_version in self.versions:
            return NegotiationResult(negotiated_version=request_version)
        # Default to latest (simplified)
        latest = sorted(self.versions.keys())[-1] if self.versions else "v1"
        return NegotiationResult(negotiated_version=latest)

    def deprecate_version(self, version: str, deprecation_date: datetime, sunset_date: datetime):
        if version in self.versions:
            self.versions[version].status = VersionStatus.DEPRECATED
            self.versions[version].deprecation_date = deprecation_date
            self.versions[version].sunset_date = sunset_date

    def get_breaking_changes(self, from_version: str, to_version: str) -> list[str]:
        changes = []
        if from_version in self.versions: changes.extend(self.versions[from_version].breaking_changes)
        if to_version in self.versions: changes.extend(self.versions[to_version].breaking_changes)
        return changes


def parse_version_from_accept_header(header: str) -> str | None:
    if "version=" in header:
        return header.split("version=")[-1].split(";")[0]
    return None
