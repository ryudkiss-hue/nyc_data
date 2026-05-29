"""Master data management for maintaining single source of truth records."""
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

__all__ = ["MasterDataManager", "MasterEntity", "get_master_record", "EntityMergeStrategy"]

class EntityMergeStrategy(Enum):
    PICK_FIRST = auto()
    PICK_LATEST = auto()

@dataclass
class MasterEntity:
    entity_id: str
    canonical_record: dict[str, Any]
    source_record_ids: list[str] = field(default_factory=list)
    entity_type: str = "unknown"

class MasterDataManager:
    def __init__(self) -> None:
        self.master_data: dict[str, dict[str, Any]] = {}
        self._entities: dict[str, MasterEntity] = {}

    def register_master_data(self, key: str, data: dict[str, Any]) -> bool:
        self.master_data[key] = data
        return True

    def register_entity(self, entity_id: str, entity: MasterEntity) -> bool:
        self._entities[entity_id] = entity
        return True

    def get_record(self, key: str) -> dict[str, Any] | None:
        return self.master_data.get(key)

    def create_master_entity(self, *records: dict[str, Any], entity_type: str = "unknown", merge_strategy: EntityMergeStrategy = EntityMergeStrategy.PICK_FIRST) -> str:
        if not records:
            raise ValueError("At least one record is required")

        entity_id = str(uuid.uuid4())
        source_ids = []
        canonical = {}

        for record in records:
            if "id" in record:
                source_ids.append(str(record["id"]))

        if merge_strategy == EntityMergeStrategy.PICK_FIRST:
            canonical = dict(records[0])
        elif merge_strategy == EntityMergeStrategy.PICK_LATEST:
            canonical = dict(records[-1])

        entity = MasterEntity(
            entity_id=entity_id,
            canonical_record=canonical,
            source_record_ids=source_ids,
            entity_type=entity_type
        )
        self._entities[entity_id] = entity
        return entity_id

    def get_master_entity(self, entity_id: str) -> MasterEntity | None:
        return self._entities.get(entity_id)

    def validate_merge(self, entity_id: str, required_fields: list[str]) -> tuple[bool, list[str]]:
        entity = self.get_master_entity(entity_id)
        if not entity:
            return False, ["Entity not found"]

        issues = []
        for f in required_fields:
            if f not in entity.canonical_record or entity.canonical_record[f] is None:
                issues.append(f"Missing required field: {f}")

        return len(issues) == 0, issues

    def get_statistics(self) -> dict[str, int]:
        return {"total_entities": len(self._entities)}

def get_master_record(key: str) -> dict[str, Any]:
    return {}
