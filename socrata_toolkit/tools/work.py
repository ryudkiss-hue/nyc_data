"""Work management and work queue handler for task orchestration."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto
from datetime import datetime, timezone
import json
import pandas as pd
from socrata_toolkit.integrations.graph import SharePointListItem, OutlookEvent, OutlookEventAttendee

__all__ = [
    "WorkItem", "WorkQueue", "create_work_item", "process_work_queue", 
    "GoogleWorkspaceAdapter", "SharePointListSync", "OutlookCalendarSync", "M365Adapter", 
    "SyncDirection", "MSProjectExporter", "ConflictResolutionStrategy", "MondayAdapter", "SyncState",
    "MondayItem", "MSProjectTask"
]

class SyncDirection(Enum):
    UPSTREAM = auto()
    DOWNSTREAM = auto()
    BIDIRECTIONAL = auto()

class ConflictResolutionStrategy(Enum):
    MANUAL_REVIEW = auto()
    SOURCE_WINS = auto()
    TARGET_WINS = auto()

@dataclass
class SyncState:
    local_id: str
    remote_id: str
    local_modified_at: datetime
    remote_modified_at: datetime
    last_sync_at: Optional[datetime] = None
    
    def has_conflict(self) -> bool:
        if not self.last_sync_at:
            return False
        return self.local_modified_at > self.last_sync_at and self.remote_modified_at > self.last_sync_at

@dataclass
class MondayItem:
    name: str
    priority: str

class MondayAdapter:
    def construction_list_to_items(self, df: pd.DataFrame) -> List[MondayItem]:
        items = []
        for _, row in df.iterrows():
            priority = "high" if row.get("_priority_score", 0) >= 0.7 else "low"
            items.append(MondayItem(name=row.get("address", ""), priority=priority))
        return items
        
    def contracts_to_items(self, df: pd.DataFrame) -> List[MondayItem]:
        items = []
        for _, row in df.iterrows():
            items.append(MondayItem(name=row.get("contract_id", ""), priority="high"))
        return items
        
    def export_items(self, path: str, items: List[MondayItem]):
        with open(path, "w") as f:
            json.dump([{"name": item.name, "priority": item.priority} for item in items], f)

@dataclass
class MSProjectTask:
    name: str
    duration_days: int

class MSProjectExporter:
    def from_contracts(self, df: pd.DataFrame) -> List[MSProjectTask]:
        tasks = []
        for _, row in df.iterrows():
            tasks.append(MSProjectTask(name=row.get("contract_id", ""), duration_days=30))
        self._tasks = tasks
        return tasks
        
    def save(self, path: str):
        with open(path, "w") as f:
            f.write("<Project>\n")
            for task in getattr(self, "_tasks", []):
                f.write(f"  <Task><Name>{task.name}</Name></Task>\n")
            f.write("</Project>")

class GoogleWorkspaceAdapter:
    @staticmethod
    def sheets_values(df: pd.DataFrame) -> dict:
        values = [df.columns.tolist()]
        values.extend(df.values.tolist())
        return {"majorDimension": "ROWS", "values": values}
        
    @staticmethod
    def calendar_event(summary: str, start_time: str, end_time: str, location: Optional[str] = None) -> dict:
        event = {"summary": summary, "start": {"dateTime": start_time}, "end": {"dateTime": end_time}}
        if location:
            event["location"] = location
        return event
        
    def export_for_sheets(self, df: pd.DataFrame, path: str):
        with open(path, "w") as f:
            json.dump(self.sheets_values(df), f)

class M365Adapter:
    @staticmethod
    def sharepoint_list_items(df: pd.DataFrame, key_columns: List[str]) -> List[dict]:
        items = []
        for _, row in df.iterrows():
            fields = {k: row[k] for k in key_columns if k in row}
            items.append({"fields": fields})
        return items
        
    @staticmethod
    def teams_notification(title: str, text: str, facts: dict) -> dict:
        return {
            "@type": "MessageCard",
            "title": title,
            "text": text,
            "sections": [{"facts": [{"name": k, "value": v} for k, v in facts.items()]}]
        }
        
    @staticmethod
    def outlook_event(subject: str, start_time: str, end_time: str, attendees: List[str]) -> dict:
        return {
            "subject": subject,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            "attendees": [{"emailAddress": {"address": a}} for a in attendees]
        }
        
    def export_payloads(self, path: str, data: dict):
        with open(path, "w") as f:
            json.dump(data, f)

class SharePointListSync:
    def __init__(self, site_id: str, list_id: str, mapping: Dict[str, str], graph_client: Any, enable_metrics: bool = False):
        self.site_id = site_id
        self.list_id = list_id
        self.mapping = mapping
        self.graph_client = graph_client
        self.enable_metrics = enable_metrics
        self._history = []
        self._conflicts = []
        
    def _parse_timestamp(self, val: Any) -> Optional[datetime]:
        if pd.isna(val):
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                if val.endswith("Z"):
                    val = val[:-1] + "+00:00"
                return datetime.fromisoformat(val)
            except ValueError:
                return None
        return None
        
    def _map_fields(self, row: pd.Series) -> dict:
        fields = {}
        for local_col, remote_col in self.mapping.items():
            val = row.get(local_col)
            if pd.isna(val):
                if local_col == "Id" or local_col == "Status":
                    fields[remote_col] = val
            else:
                fields[remote_col] = val
        return fields
        
    def _detect_conflict(self, item: SharePointListItem, local_modified: datetime) -> bool:
        if not item.modified:
            return False
        from datetime import timedelta
        return item.modified > local_modified + timedelta(seconds=1)

    def sync_from_dataverse(
        self, df: pd.DataFrame, id_column: str = "Id", modified_column: str = "ModifiedOn", 
        direction: SyncDirection = SyncDirection.UPSTREAM, 
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MANUAL_REVIEW
    ) -> Tuple[int, int, List[dict]]:
        created = 0
        updated = 0
        
        try:
            existing = self.graph_client.sharepoint_list_get_items(self.site_id, self.list_id)
        except Exception:
            raise
        
        existing_map = {}
        for item in existing:
            ext_id = item.fields.get("ExternalId")
            if ext_id:
                existing_map[ext_id] = item

        for _, row in df.iterrows():
            local_id = row.get(id_column)
            if pd.isna(local_id):
                continue
                
            local_mod = self._parse_timestamp(row.get(modified_column))
            if not local_mod:
                local_mod = datetime.now(timezone.utc)
                
            fields = self._map_fields(row)
            fields = {k: v for k, v in fields.items() if not pd.isna(v)}
            
            existing_item = existing_map.get(local_id)
            if existing_item:
                if self._detect_conflict(existing_item, local_mod):
                    self._conflicts.append({"id": local_id})
                    if conflict_strategy == ConflictResolutionStrategy.MANUAL_REVIEW:
                        continue
                self.graph_client.sharepoint_list_update_item(self.site_id, self.list_id, existing_item.id, fields)
                updated += 1
            else:
                self.graph_client.sharepoint_list_create_item(self.site_id, self.list_id, fields)
                created += 1

        self._history.append({"action": "sync", "conflicts": self._conflicts})
        return created, updated, self._conflicts
        
    def get_sync_history(self) -> List[dict]:
        return self._history
        
    def get_conflicts(self) -> List[dict]:
        return self._conflicts

class OutlookCalendarSync:
    def __init__(self, supervisor_mailbox: str, contractor_mailbox: str = "", graph_client: Any = None, enable_metrics: bool = False):
        self.supervisor_mailbox = supervisor_mailbox
        self.contractor_mailbox = contractor_mailbox
        self.graph_client = graph_client
        self.enable_metrics = enable_metrics
        self._event_map = {}
        self._history = []
        
    def create_repair_event(
        self, work_order_id: str, title: str, start_time: str, end_time: str, 
        location: str = "", description: str = "", attendees: List[str] = None
    ) -> Tuple[str, bool]:
        if not self.graph_client:
            return "", False
            
        attendees_list = []
        if attendees:
            for a in attendees:
                attendees_list.append(OutlookEventAttendee(email=a))
                
        ical_uid = f"wo-{work_order_id}@nycdot.gov"
        event = OutlookEvent(
            subject=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            body=description,
            attendees=attendees_list,
            ical_uid=ical_uid
        )
        try:
            created = self.graph_client.outlook_create_event(self.supervisor_mailbox, event)
            self._event_map[work_order_id] = created
            self._history.append({"work_order_id": work_order_id, "action": "created"})
            return created.id, True
        except Exception:
            return "", False
            
    def update_repair_event(self, work_order_id: str, start_time: str = None, end_time: str = None, status: str = None) -> bool:
        if not self.graph_client or work_order_id not in self._event_map:
            return False
            
        event = self._event_map[work_order_id]
        if start_time:
            event.start_time = start_time
        if end_time:
            event.end_time = end_time
        if status:
            event.body = f"[{status}] " + (event.body or "")
            
        try:
            updated = self.graph_client.outlook_update_event(self.supervisor_mailbox, event.id, event)
            self._event_map[work_order_id] = updated
            self._history.append({"work_order_id": work_order_id, "action": "updated"})
            return True
        except Exception:
            return False
            
    def get_sync_history(self) -> List[dict]:
        return self._history

@dataclass
class WorkItem:
    task: str
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkQueue:
    items: List[WorkItem] = field(default_factory=list)

    def add_item(self, item: WorkItem) -> None:
        self.items.append(item)

    def process(self) -> List[WorkItem]:
        return []

def create_work_item(task: str) -> WorkItem:
    return WorkItem(task=task)

def process_work_queue() -> List[WorkItem]:
    return []
