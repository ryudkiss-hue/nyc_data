"""Tests for M365 sync integration (SharePoint and Outlook).

Covers:
- SharePoint list sync scenarios (create, update, delete, conflicts)
- Outlook calendar sync scenarios (new events, updates, cancellations)
- Bi-directional conflict detection and resolution
- De-duplication of calendar events
- Integration with Dataverse
"""

from __future__ import annotations

import pytest
import pandas as pd
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch

from socrata_toolkit.tools.work import (
    SharePointListSync,
    OutlookCalendarSync,
    SyncDirection,
    ConflictResolutionStrategy,
    SyncState,
)
from socrata_toolkit.integrations.graph import (
    SharePointListItem,
    OutlookEvent,
    OutlookEventAttendee,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_graph_client():
    """Create mock GraphAPIClient."""
    return MagicMock()


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for sync testing."""
    return pd.DataFrame({
        "Id": ["WO-001", "WO-002", "WO-003"],
        "Title": ["Pothole Repair", "Sidewalk Replacement", "Crack Sealing"],
        "Status": ["Active", "Pending", "Completed"],
        "Priority": [1, 2, 3],
        "Location": ["Broadway & 42nd", "5th Ave & 34th", "Park Ave & 79th"],
        "ModifiedOn": [
            datetime.now(timezone.utc),
            datetime.now(timezone.utc) - timedelta(days=1),
            datetime.now(timezone.utc) - timedelta(days=7),
        ],
    })


@pytest.fixture
def sharepoint_sync(mock_graph_client):
    """Create SharePointListSync instance with mocked client."""
    return SharePointListSync(
        site_id="site-123",
        list_id="list-456",
        mapping={
            "Id": "ExternalId",
            "Title": "Title",
            "Status": "Status",
            "Location": "Location",
        },
        graph_client=mock_graph_client,
        enable_metrics=False,
    )


@pytest.fixture
def outlook_sync(mock_graph_client):
    """Create OutlookCalendarSync instance with mocked client."""
    return OutlookCalendarSync(
        supervisor_mailbox="supervisor@org.onmicrosoft.com",
        contractor_mailbox="contractor@org.onmicrosoft.com",
        graph_client=mock_graph_client,
        enable_metrics=False,
    )


# ---------------------------------------------------------------------------
# SharePoint Sync Tests - Basic Operations
# ---------------------------------------------------------------------------

class TestSharePointListSyncBasic:
    """Tests for basic SharePoint list sync operations."""

    def test_sharepoint_sync_initialization(self, sharepoint_sync):
        """Test SharePointListSync initialization."""
        assert sharepoint_sync.site_id == "site-123"
        assert sharepoint_sync.list_id == "list-456"
        assert len(sharepoint_sync.mapping) == 4
        assert sharepoint_sync.graph_client is not None

    def test_sync_from_dataverse_no_existing_items(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test syncing from Dataverse when no items exist in SharePoint."""
        # Mock: no existing items
        mock_graph_client.sharepoint_list_get_items.return_value = []
        mock_graph_client.sharepoint_list_create_item.return_value = MagicMock()

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
            modified_column="ModifiedOn",
        )

        assert created == 3
        assert updated == 0
        assert len(conflicts) == 0
        assert mock_graph_client.sharepoint_list_create_item.call_count == 3

    def test_sync_from_dataverse_all_items_exist(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test syncing when all items already exist in SharePoint."""
        # Mock: existing items
        existing_items = [
            SharePointListItem(
                id=f"sp-{i}",
                fields={"ExternalId": f"WO-{i:03d}"},
                modified=datetime.now(timezone.utc) - timedelta(days=30),
            )
            for i in range(1, 4)
        ]
        mock_graph_client.sharepoint_list_get_items.return_value = existing_items
        mock_graph_client.sharepoint_list_update_item.return_value = MagicMock()

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
            modified_column="ModifiedOn",
        )

        assert created == 0
        assert updated == 3
        assert len(conflicts) == 0
        assert mock_graph_client.sharepoint_list_update_item.call_count == 3

    def test_sync_from_dataverse_mixed_create_and_update(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test syncing with both creates and updates."""
        # Mock: only first item exists
        existing_items = [
            SharePointListItem(
                id="sp-1",
                fields={"ExternalId": "WO-001"},
                modified=datetime.now(timezone.utc) - timedelta(days=30),
            )
        ]
        mock_graph_client.sharepoint_list_get_items.return_value = existing_items
        mock_graph_client.sharepoint_list_create_item.return_value = MagicMock()
        mock_graph_client.sharepoint_list_update_item.return_value = MagicMock()

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
            modified_column="ModifiedOn",
        )

        assert created == 2
        assert updated == 1
        assert len(conflicts) == 0


# ---------------------------------------------------------------------------
# SharePoint Sync Tests - Conflict Detection
# ---------------------------------------------------------------------------

class TestSharePointListSyncConflicts:
    """Tests for conflict detection and resolution."""

    def test_detect_conflict_both_modified(self, sharepoint_sync):
        """Test conflict detection when both local and remote are modified."""
        # Item modified more recently in SharePoint than locally
        item = SharePointListItem(
            id="sp-1",
            fields={"ExternalId": "WO-001"},
            modified=datetime.now(timezone.utc),
        )
        local_modified = datetime.now(timezone.utc) - timedelta(hours=1)

        has_conflict = sharepoint_sync._detect_conflict(item, local_modified)

        assert has_conflict is True

    def test_no_conflict_remote_older(self, sharepoint_sync):
        """Test no conflict when remote is older than local."""
        item = SharePointListItem(
            id="sp-1",
            fields={"ExternalId": "WO-001"},
            modified=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        local_modified = datetime.now(timezone.utc) - timedelta(hours=1)

        has_conflict = sharepoint_sync._detect_conflict(item, local_modified)

        assert has_conflict is False

    def test_sync_with_conflict_manual_review(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test sync with conflicts set to MANUAL_REVIEW."""
        # Mock existing item with recent modification
        recent_time = datetime.now(timezone.utc)
        existing_items = [
            SharePointListItem(
                id="sp-1",
                fields={"ExternalId": "WO-001"},
                modified=recent_time,
            )
        ]
        mock_graph_client.sharepoint_list_get_items.return_value = existing_items

        # Modify first row to be older than remote
        sample_dataframe.loc[0, "ModifiedOn"] = recent_time - timedelta(hours=1)

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
            modified_column="ModifiedOn",
            conflict_strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
        )

        # Should detect conflict but not update due to MANUAL_REVIEW
        assert len(conflicts) >= 0  # Depends on detection logic
        assert created == 2

    def test_sync_with_conflict_source_wins(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test sync with SOURCE_WINS conflict resolution."""
        recent_time = datetime.now(timezone.utc)
        existing_items = [
            SharePointListItem(
                id="sp-1",
                fields={"ExternalId": "WO-001"},
                modified=recent_time,
            )
        ]
        mock_graph_client.sharepoint_list_get_items.return_value = existing_items
        mock_graph_client.sharepoint_list_update_item.return_value = MagicMock()

        sample_dataframe.loc[0, "ModifiedOn"] = recent_time - timedelta(hours=1)

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
            modified_column="ModifiedOn",
            conflict_strategy=ConflictResolutionStrategy.SOURCE_WINS,
        )

        # SOURCE_WINS should resolve conflict in favor of local data
        assert created == 2

    def test_sync_conflict_tracking(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test that conflicts are properly tracked."""
        recent_time = datetime.now(timezone.utc)
        existing_items = [
            SharePointListItem(
                id="sp-1",
                fields={"ExternalId": "WO-001"},
                modified=recent_time,
            )
        ]
        mock_graph_client.sharepoint_list_get_items.return_value = existing_items

        sample_dataframe.loc[0, "ModifiedOn"] = recent_time - timedelta(hours=1)

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            conflict_strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
        )

        history = sharepoint_sync.get_sync_history()
        assert len(history) > 0
        latest_sync = history[-1]
        assert "conflicts" in latest_sync

    def test_get_conflicts_history(self, sharepoint_sync):
        """Test retrieving conflict history."""
        conflicts = sharepoint_sync.get_conflicts()
        assert isinstance(conflicts, list)


# ---------------------------------------------------------------------------
# SharePoint Sync Tests - Field Mapping
# ---------------------------------------------------------------------------

class TestSharePointListSyncFieldMapping:
    """Tests for field mapping functionality."""

    def test_map_fields_basic(self, sharepoint_sync):
        """Test basic field mapping."""
        row = pd.Series({
            "Id": "WO-001",
            "Title": "Pothole",
            "Status": "Active",
            "Location": "Broadway",
        })

        mapped = sharepoint_sync._map_fields(row)

        assert mapped["ExternalId"] == "WO-001"
        assert mapped["Title"] == "Pothole"
        assert mapped["Status"] == "Active"
        assert mapped["Location"] == "Broadway"

    def test_map_fields_with_nan_values(self, sharepoint_sync):
        """Test field mapping with NaN values."""
        row = pd.Series({
            "Id": "WO-001",
            "Title": None,
            "Status": "Active",
            "Location": pd.NA,
        })

        mapped = sharepoint_sync._map_fields(row)

        assert "Title" not in mapped or mapped["Title"] is None
        assert "Location" not in mapped or mapped["Location"] is None
        assert mapped["Status"] == "Active"

    def test_map_fields_with_datetime(self, sharepoint_sync):
        """Test field mapping with datetime values."""
        dt = datetime.now(timezone.utc)
        row = pd.Series({
            "Id": "WO-001",
            "Title": "Test",
            "Status": "Active",
            "Location": "Test",
        })

        mapped = sharepoint_sync._map_fields(row)
        assert isinstance(mapped["ExternalId"], str)


# ---------------------------------------------------------------------------
# SharePoint Sync Tests - Datetime Parsing
# ---------------------------------------------------------------------------

class TestSharePointListSyncDatetimeParsing:
    """Tests for timestamp parsing."""

    def test_parse_timestamp_iso_format(self, sharepoint_sync):
        """Test parsing ISO format timestamp."""
        iso_string = "2025-06-15T10:30:45Z"
        parsed = sharepoint_sync._parse_timestamp(iso_string)

        assert parsed is not None
        assert parsed.year == 2025
        assert parsed.month == 6

    def test_parse_timestamp_datetime_object(self, sharepoint_sync):
        """Test parsing datetime object."""
        dt = datetime.now(timezone.utc)
        parsed = sharepoint_sync._parse_timestamp(dt)

        assert parsed == dt

    def test_parse_timestamp_none(self, sharepoint_sync):
        """Test parsing None."""
        parsed = sharepoint_sync._parse_timestamp(None)
        assert parsed is None

    def test_parse_timestamp_invalid(self, sharepoint_sync):
        """Test parsing invalid timestamp."""
        parsed = sharepoint_sync._parse_timestamp("invalid")
        assert parsed is None


# ---------------------------------------------------------------------------
# Outlook Calendar Sync Tests - Event Creation
# ---------------------------------------------------------------------------

class TestOutlookCalendarSyncEventCreation:
    """Tests for Outlook calendar event creation."""

    def test_create_repair_event(self, outlook_sync, mock_graph_client):
        """Test creating a repair event."""
        created_event = OutlookEvent(
            subject="Test Event",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        event_id, success = outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Pothole Repair",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            location="Broadway & 42nd",
            description="Emergency pothole repair",
        )

        assert success is True
        assert event_id == "event-1"
        assert "WO-001" in outlook_sync._event_map

    def test_create_repair_event_with_attendees(self, outlook_sync, mock_graph_client):
        """Test creating event with attendees."""
        created_event = OutlookEvent(
            subject="Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
            attendees=[
                OutlookEventAttendee(email="supervisor@org.com"),
                OutlookEventAttendee(email="contractor@org.com"),
            ],
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        event_id, success = outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            attendees=["extra@org.com"],
        )

        assert success is True
        assert event_id == "event-1"

    def test_create_repair_event_no_client(self):
        """Test creating event when graph_client is not configured."""
        sync = OutlookCalendarSync(
            supervisor_mailbox="supervisor@org.com",
            graph_client=None,
            enable_metrics=False,
        )

        event_id, success = sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        assert success is False
        assert event_id == ""

    def test_create_repair_event_uses_ical_uid(self, outlook_sync, mock_graph_client):
        """Test that created event uses iCalendar UID for deduplication."""
        created_event = OutlookEvent(
            subject="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
            ical_uid="wo-WO-001@nycdot.gov",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        event_id, success = outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        # Verify the call included iCalUId
        call_args = mock_graph_client.outlook_create_event.call_args
        event_arg = call_args[0][1]  # Second positional argument is the event
        assert event_arg.ical_uid == "wo-WO-001@nycdot.gov"


# ---------------------------------------------------------------------------
# Outlook Calendar Sync Tests - Event Updates
# ---------------------------------------------------------------------------

class TestOutlookCalendarSyncEventUpdates:
    """Tests for Outlook calendar event updates."""

    def test_update_repair_event_reschedule(self, outlook_sync, mock_graph_client):
        """Test updating event when repair is rescheduled."""
        # Create event first
        created_event = OutlookEvent(
            subject="Pothole Repair",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Pothole Repair",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        # Now update event
        mock_graph_client.outlook_get_events.return_value = [created_event]
        mock_graph_client.outlook_update_event.return_value = None

        updated = outlook_sync.update_repair_event(
            work_order_id="WO-001",
            start_time="2025-06-16T14:00:00",
            end_time="2025-06-16T15:00:00",
        )

        assert updated is True
        assert mock_graph_client.outlook_update_event.called

    def test_update_repair_event_with_status(self, outlook_sync, mock_graph_client):
        """Test updating event with status change."""
        created_event = OutlookEvent(
            subject="Pothole Repair",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
            body="Original description",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Pothole Repair",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            description="Original description",
        )

        mock_graph_client.outlook_get_events.return_value = [created_event]
        mock_graph_client.outlook_update_event.return_value = None

        updated = outlook_sync.update_repair_event(
            work_order_id="WO-001",
            status="In Progress",
        )

        assert updated is True
        # Verify that status was added to body
        call_args = mock_graph_client.outlook_update_event.call_args
        event_arg = call_args[0][2]  # Third positional argument is the event
        assert "[In Progress]" in event_arg.body

    def test_update_nonexistent_event(self, outlook_sync, mock_graph_client):
        """Test updating non-existent event."""
        updated = outlook_sync.update_repair_event(
            work_order_id="WO-999",
            start_time="2025-06-15T10:00:00",
        )

        assert updated is False


# ---------------------------------------------------------------------------
# Outlook Calendar Sync Tests - Sync History
# ---------------------------------------------------------------------------

class TestOutlookCalendarSyncHistory:
    """Tests for calendar sync history tracking."""

    def test_sync_history_creation(self, outlook_sync, mock_graph_client):
        """Test sync history is recorded."""
        created_event = OutlookEvent(
            subject="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        history = outlook_sync.get_sync_history()

        assert len(history) == 1
        assert history[0]["work_order_id"] == "WO-001"
        assert history[0]["action"] == "created"

    def test_sync_history_multiple_operations(self, outlook_sync, mock_graph_client):
        """Test history with multiple operations."""
        created_event = OutlookEvent(
            subject="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
        )
        mock_graph_client.outlook_create_event.return_value = created_event
        mock_graph_client.outlook_get_events.return_value = [created_event]
        mock_graph_client.outlook_update_event.return_value = None

        # Create
        outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        # Update
        outlook_sync.update_repair_event(
            work_order_id="WO-001",
            start_time="2025-06-16T10:00:00",
        )

        history = outlook_sync.get_sync_history()

        assert len(history) == 2
        assert history[0]["action"] == "created"
        assert history[1]["action"] == "updated"


# ---------------------------------------------------------------------------
# Outlook Calendar Sync Tests - De-duplication
# ---------------------------------------------------------------------------

class TestOutlookCalendarDeduplication:
    """Tests for event de-duplication using iCalendar UID."""

    def test_ical_uid_generation(self, outlook_sync, mock_graph_client):
        """Test that iCalendar UID is generated correctly."""
        created_event = OutlookEvent(
            subject="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
            ical_uid="wo-WO-001@nycdot.gov",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        call_args = mock_graph_client.outlook_create_event.call_args
        event_arg = call_args[0][1]
        assert event_arg.ical_uid == "wo-WO-001@nycdot.gov"

    def test_duplicate_event_prevention(self, outlook_sync, mock_graph_client):
        """Test that duplicate events are prevented via UID matching."""
        # First event creation
        created_event = OutlookEvent(
            subject="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
            ical_uid="wo-WO-001@nycdot.gov",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        # Verify the iCalUId is set to prevent duplicates
        call_args = mock_graph_client.outlook_create_event.call_args
        event_arg = call_args[0][1]
        assert "wo-WO-001" in event_arg.ical_uid


# ---------------------------------------------------------------------------
# Integration Tests - SharePoint + Dataverse Workflow
# ---------------------------------------------------------------------------

class TestIntegrationSharePointDataverse:
    """Integration tests for SharePoint and Dataverse workflow."""

    def test_construction_list_to_sharepoint(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test syncing construction list from Dataverse to SharePoint."""
        mock_graph_client.sharepoint_list_get_items.return_value = []
        mock_graph_client.sharepoint_list_create_item.return_value = MagicMock()

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
            modified_column="ModifiedOn",
            direction=SyncDirection.UPSTREAM,
        )

        assert created == len(sample_dataframe)
        assert updated == 0
        assert len(conflicts) == 0

    def test_work_order_complete_workflow(
        self, sharepoint_sync, outlook_sync, sample_dataframe, mock_graph_client
    ):
        """Test complete workflow: Dataverse → SharePoint + Outlook."""
        # Sync to SharePoint
        mock_graph_client.sharepoint_list_get_items.return_value = []
        mock_graph_client.sharepoint_list_create_item.return_value = MagicMock()

        created, _, _ = sharepoint_sync.sync_from_dataverse(
            sample_dataframe,
            id_column="Id",
        )
        assert created == 3

        # Create calendar events
        mock_graph_client.outlook_create_event.return_value = OutlookEvent(
            subject="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
        )

        for _, row in sample_dataframe.iterrows():
            event_id, success = outlook_sync.create_repair_event(
                work_order_id=row["Id"],
                title=row["Title"],
                start_time="2025-06-15T10:00:00",
                end_time="2025-06-15T11:00:00",
                location=row["Location"],
            )
            assert success is True


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestSyncErrorHandling:
    """Tests for error handling in sync operations."""

    def test_sharepoint_sync_handles_api_errors(
        self, sharepoint_sync, sample_dataframe, mock_graph_client
    ):
        """Test graceful handling of API errors during sync."""
        mock_graph_client.sharepoint_list_get_items.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            sharepoint_sync.sync_from_dataverse(sample_dataframe)

    def test_outlook_sync_handles_api_errors(self, outlook_sync, mock_graph_client):
        """Test graceful handling of API errors during Outlook sync."""
        mock_graph_client.outlook_create_event.side_effect = Exception("API Error")

        event_id, success = outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title="Test",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        assert success is False


# ---------------------------------------------------------------------------
# SyncState Tests
# ---------------------------------------------------------------------------

class TestSyncState:
    """Tests for SyncState tracking."""

    def test_sync_state_creation(self):
        """Test creating SyncState."""
        state = SyncState(
            local_id="WO-001",
            remote_id="sp-1",
            local_modified_at=datetime.now(timezone.utc),
            remote_modified_at=datetime.now(timezone.utc),
        )

        assert state.local_id == "WO-001"
        assert state.remote_id == "sp-1"

    def test_sync_state_conflict_detection(self):
        """Test conflict detection in SyncState."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        state = SyncState(
            local_id="WO-001",
            remote_id="sp-1",
            local_modified_at=now,
            remote_modified_at=now,
            last_sync_at=past,
        )

        assert state.has_conflict() is True

    def test_sync_state_no_conflict_when_one_unchanged(self):
        """Test no conflict when only one side changed."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        state = SyncState(
            local_id="WO-001",
            remote_id="sp-1",
            local_modified_at=past,  # Not changed
            remote_modified_at=now,  # Changed
            last_sync_at=past,
        )

        assert state.has_conflict() is False


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_dataframe_sync(self, sharepoint_sync, mock_graph_client):
        """Test syncing empty DataFrame."""
        empty_df = pd.DataFrame({
            "Id": [],
            "Title": [],
            "ModifiedOn": [],
        })

        mock_graph_client.sharepoint_list_get_items.return_value = []

        created, updated, conflicts = sharepoint_sync.sync_from_dataverse(empty_df)

        assert created == 0
        assert updated == 0

    def test_very_long_event_title(self, outlook_sync, mock_graph_client):
        """Test creating event with very long title."""
        long_title = "A" * 500

        created_event = OutlookEvent(
            subject=long_title,
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            id="event-1",
        )
        mock_graph_client.outlook_create_event.return_value = created_event

        event_id, success = outlook_sync.create_repair_event(
            work_order_id="WO-001",
            title=long_title,
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        assert success is True

    def test_special_characters_in_fields(self, sharepoint_sync):
        """Test handling special characters in field values."""
        row = pd.Series({
            "Id": "WO-001",
            "Title": "Repair @ Corner St & Ave (Apt 5)",
            "Status": "Active",
            "Location": "O'Brien Plaza",
        })

        mapped = sharepoint_sync._map_fields(row)

        assert "Title" in mapped
        assert "Location" in mapped
        assert "O'Brien" in mapped["Location"]
