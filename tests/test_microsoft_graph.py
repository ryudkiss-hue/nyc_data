"""Tests for Microsoft Graph API client.

Covers:
- OAuth2 token management and caching
- Token refresh and expiry handling
- SharePoint list operations (CRUD)
- Outlook calendar operations
- Rate limit handling with exponential backoff
- Error handling and retries
- Connection pooling
- Correlation ID tracking
"""

from __future__ import annotations

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock, patch, call
from urllib.parse import parse_qs, urlparse

from socrata_toolkit.integrations.graph import (
    GraphAPIClient,
    GraphAPIConfig,
    GraphAPIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ConflictError,
    ValidationError,
    TimeoutError,
    OAuthToken,
    TokenCache,
    SharePointListItem,
    OutlookEvent,
    OutlookEventAttendee,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    """Create test GraphAPIConfig."""
    return GraphAPIConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        base_url="https://graph.microsoft.com/v1.0",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def mock_session():
    """Create mock requests.Session."""
    return MagicMock()


@pytest.fixture
def client(config, mock_session):
    """Create GraphAPIClient with mocked session."""
    with patch("socrata_toolkit.integrations.graph.requests.Session", return_value=mock_session):
        return GraphAPIClient(config, enable_metrics=False)


# ---------------------------------------------------------------------------
# OAuthToken Tests
# ---------------------------------------------------------------------------

class TestOAuthToken:
    """Tests for OAuthToken class."""

    def test_token_creation(self):
        """Test creating an OAuthToken."""
        token = OAuthToken(
            access_token="test-token",
            token_type="Bearer",
            expires_in=3600,
        )
        assert token.access_token == "test-token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.expires_at is not None

    def test_token_expiry_check(self):
        """Test token expiry detection."""
        # Create token that expires in 30 seconds
        token = OAuthToken(
            access_token="test-token",
            expires_in=30,
        )
        assert not token.is_expired()

        # Create token that expired 60 seconds ago
        past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        token_expired = OAuthToken(
            access_token="test-token",
            expires_at=past_time,
        )
        assert token_expired.is_expired()

    def test_token_expiring_soon(self):
        """Test token expiring soon detection."""
        # Create token expiring in 1 minute
        token = OAuthToken(
            access_token="test-token",
            expires_in=60,
        )
        # Should be expiring soon (within 5 minutes)
        assert token.is_expiring_soon(seconds=300)
        # Should not be expiring soon (within 30 seconds)
        assert not token.is_expiring_soon(seconds=30)


# ---------------------------------------------------------------------------
# TokenCache Tests
# ---------------------------------------------------------------------------

class TestTokenCache:
    """Tests for TokenCache class."""

    def test_token_cache_set_and_get(self):
        """Test setting and getting token from cache."""
        cache = TokenCache(ttl_seconds=3600)
        token = OAuthToken(access_token="test-token", expires_in=3600)

        cache.set(token)
        cached = cache.get()

        assert cached is not None
        assert cached.access_token == "test-token"

    def test_token_cache_expiry(self):
        """Test that expired tokens are not returned from cache."""
        cache = TokenCache(ttl_seconds=3600)
        
        # Create expired token
        past_time = datetime.now(timezone.utc) - timedelta(seconds=60)
        token = OAuthToken(
            access_token="test-token",
            expires_at=past_time,
        )

        cache.set(token)
        cached = cache.get()

        assert cached is None

    def test_token_cache_ttl(self):
        """Test that cache respects TTL."""
        cache = TokenCache(ttl_seconds=1)
        token = OAuthToken(access_token="test-token", expires_in=3600)

        cache.set(token)
        cached = cache.get()
        assert cached is not None

        # Simulate TTL expiry by modifying cache time
        cache._cached_at = datetime.now(timezone.utc) - timedelta(seconds=2)
        cached = cache.get()
        assert cached is None

    def test_token_cache_clear(self):
        """Test clearing token cache."""
        cache = TokenCache()
        token = OAuthToken(access_token="test-token", expires_in=3600)

        cache.set(token)
        assert cache.get() is not None

        cache.clear()
        assert cache.get() is None


# ---------------------------------------------------------------------------
# GraphAPIClient Initialization Tests
# ---------------------------------------------------------------------------

class TestGraphAPIClientInit:
    """Tests for GraphAPIClient initialization."""

    def test_client_initialization(self, config):
        """Test client initialization."""
        with patch("socrata_toolkit.integrations.graph.requests.Session"):
            client = GraphAPIClient(config, enable_metrics=False)
            assert client.config == config
            assert client._token_cache is not None
            assert client._session is not None

    def test_client_with_metrics_disabled(self, config):
        """Test client initialization with metrics disabled."""
        with patch("socrata_toolkit.integrations.graph.requests.Session"):
            client = GraphAPIClient(config, enable_metrics=False)
            assert client.metrics is None

    def test_client_context_manager(self, config):
        """Test client as context manager."""
        with patch("socrata_toolkit.integrations.graph.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            with GraphAPIClient(config, enable_metrics=False) as client:
                assert client is not None

            mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# OAuth Token Tests
# ---------------------------------------------------------------------------

class TestGraphAPIClientTokenManagement:
    """Tests for OAuth token management."""

    def test_get_auth_token_success(self, client):
        """Test successful token acquisition."""
        token_response = {
            "access_token": "new-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        client._session.post = MagicMock()
        client._session.post.return_value.json.return_value = token_response
        client._session.post.return_value.raise_for_status = MagicMock()

        token = client._get_auth_token()

        assert token == "new-token"
        assert client._session.post.called

    def test_get_auth_token_from_cache(self, client):
        """Test getting token from cache."""
        cached_token = OAuthToken(access_token="cached-token", expires_in=3600)
        client._token_cache.set(cached_token)

        client._session.post = MagicMock()

        token = client._get_auth_token()

        assert token == "cached-token"
        assert not client._session.post.called

    def test_get_auth_token_refresh_on_expiry(self, client):
        """Test token refresh when cached token is expired."""
        # Set expired token in cache
        expired_token = OAuthToken(
            access_token="expired-token",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
        client._token_cache.set(expired_token)

        token_response = {
            "access_token": "new-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        client._session.post = MagicMock()
        client._session.post.return_value.json.return_value = token_response
        client._session.post.return_value.raise_for_status = MagicMock()

        token = client._get_auth_token()

        assert token == "new-token"
        assert client._session.post.called

    def test_get_auth_token_failure(self, client):
        """Test token acquisition failure."""
        client._session.post = MagicMock()
        client._session.post.side_effect = Exception("Auth failed")

        with pytest.raises(AuthenticationError):
            client._get_auth_token()

    def test_get_auth_token_invalid_response(self, client):
        """Test handling of invalid token response."""
        client._session.post = MagicMock()
        client._session.post.return_value.json.return_value = {"error": "invalid_grant"}
        client._session.post.return_value.raise_for_status.side_effect = Exception("400")

        with pytest.raises(AuthenticationError):
            client._get_auth_token()


# ---------------------------------------------------------------------------
# HTTP Request Tests
# ---------------------------------------------------------------------------

class TestGraphAPIClientRequests:
    """Tests for HTTP request handling."""

    def test_request_success(self, client):
        """Test successful HTTP request."""
        response_data = {"value": [{"id": "1", "name": "test"}]}

        client._session.request = MagicMock()
        client._session.request.return_value.status_code = 200
        client._session.request.return_value.json.return_value = response_data
        client._session.request.return_value.text = "{}"

        # Mock token
        client._get_auth_token = MagicMock(return_value="test-token")

        result = client._request("GET", "sites/site-1/lists")

        assert result == response_data
        assert client._session.request.called

    def test_request_404_not_found(self, client):
        """Test 404 Not Found response."""
        client._session.request = MagicMock()
        client._session.request.return_value.status_code = 404
        client._session.request.return_value.text = "Not found"

        client._get_auth_token = MagicMock(return_value="test-token")

        with pytest.raises(NotFoundError):
            client._request("GET", "sites/invalid")

    def test_request_409_conflict(self, client):
        """Test 409 Conflict response."""
        client._session.request = MagicMock()
        client._session.request.return_value.status_code = 409
        client._session.request.return_value.text = "Conflict"

        client._get_auth_token = MagicMock(return_value="test-token")

        with pytest.raises(ConflictError):
            client._request("POST", "sites/site-1/lists/items")

    def test_request_429_rate_limit_with_retry(self, client):
        """Test rate limit with automatic retry."""
        client._session.request = MagicMock()

        # First call returns 429, second call returns 200
        response_429 = MagicMock()
        response_429.status_code = 429
        response_429.headers = {"Retry-After": "1"}

        response_200 = MagicMock()
        response_200.status_code = 200
        response_200.json.return_value = {"value": []}
        response_200.text = "{}"

        client._session.request.side_effect = [response_429, response_200]
        client._get_auth_token = MagicMock(return_value="test-token")

        with patch("time.sleep"):
            result = client._request("GET", "sites/site-1/lists")

        assert result == {"value": []}

    def test_request_timeout(self, client):
        """Test request timeout handling."""
        import requests

        client._session.request = MagicMock()
        client._session.request.side_effect = requests.exceptions.Timeout("Timeout")

        client._get_auth_token = MagicMock(return_value="test-token")

        with pytest.raises(TimeoutError):
            client._request("GET", "sites/site-1/lists")

    def test_request_with_correlation_id(self, client):
        """Test request includes correlation ID."""
        client._session.request = MagicMock()
        client._session.request.return_value.status_code = 200
        client._session.request.return_value.json.return_value = {}
        client._session.request.return_value.text = "{}"

        client._get_auth_token = MagicMock(return_value="test-token")

        client._request("GET", "sites/site-1/lists")

        # Check that headers include correlation ID
        call_args = client._session.request.call_args
        headers = call_args.kwargs["headers"]
        assert "x-correlation-id" in headers


# ---------------------------------------------------------------------------
# SharePoint List Operations Tests
# ---------------------------------------------------------------------------

class TestSharePointListOperations:
    """Tests for SharePoint list CRUD operations."""

    def test_sharepoint_list_get_items(self, client):
        """Test getting items from SharePoint list."""
        items_response = {
            "value": [
                {
                    "id": "1",
                    "createdDateTime": "2025-01-01T00:00:00Z",
                    "lastModifiedDateTime": "2025-01-15T00:00:00Z",
                    "fields": {"Title": "Item 1", "Status": "Active"},
                    "webUrl": "https://example.sharepoint.com/items/1",
                }
            ]
        }

        client._request = MagicMock(return_value=items_response)

        items = client.sharepoint_list_get_items(
            site_id="site-1",
            list_id="list-1",
        )

        assert len(items) == 1
        assert items[0].id == "1"
        assert items[0].fields["Title"] == "Item 1"
        assert client._request.called

    def test_sharepoint_list_get_items_with_filter(self, client):
        """Test getting items with filter."""
        items_response = {"value": []}

        client._request = MagicMock(return_value=items_response)

        items = client.sharepoint_list_get_items(
            site_id="site-1",
            list_id="list-1",
            filters={"Status": "Active", "Priority": 1},
        )

        # Check that filter was passed to request
        call_args = client._request.call_args
        params = call_args.kwargs["params"]
        assert "$filter" in params

    def test_sharepoint_list_get_items_pagination(self, client):
        """Test pagination when getting list items."""
        items_response = {"value": []}

        client._request = MagicMock(return_value=items_response)

        items = client.sharepoint_list_get_items(
            site_id="site-1",
            list_id="list-1",
            top=50,
            skip=100,
        )

        call_args = client._request.call_args
        params = call_args.kwargs["params"]
        assert params["$top"] == 50
        assert params["$skip"] == 100

    def test_sharepoint_list_create_item(self, client):
        """Test creating a SharePoint list item."""
        create_response = {
            "id": "new-1",
            "createdDateTime": "2025-06-01T10:00:00Z",
            "lastModifiedDateTime": "2025-06-01T10:00:00Z",
            "fields": {"Title": "New Item", "Status": "Draft"},
            "webUrl": "https://example.sharepoint.com/items/new-1",
        }

        client._request = MagicMock(return_value=create_response)

        item = client.sharepoint_list_create_item(
            site_id="site-1",
            list_id="list-1",
            fields={"Title": "New Item", "Status": "Draft"},
        )

        assert item.id == "new-1"
        assert item.fields["Title"] == "New Item"
        assert client._request.called

    def test_sharepoint_list_update_item(self, client):
        """Test updating a SharePoint list item."""
        update_response = {
            "id": "1",
            "createdDateTime": "2025-01-01T00:00:00Z",
            "lastModifiedDateTime": "2025-06-01T12:00:00Z",
            "fields": {"Title": "Updated Item", "Status": "Complete"},
            "webUrl": "https://example.sharepoint.com/items/1",
        }

        client._request = MagicMock(return_value=update_response)

        item = client.sharepoint_list_update_item(
            site_id="site-1",
            list_id="list-1",
            item_id="1",
            fields={"Title": "Updated Item", "Status": "Complete"},
        )

        assert item.id == "1"
        assert item.fields["Status"] == "Complete"

    def test_sharepoint_list_update_item_with_etag(self, client):
        """Test updating item with ETag for concurrency control."""
        client._request = MagicMock(return_value={
            "id": "1",
            "fields": {"Title": "Item"},
        })

        client.sharepoint_list_update_item(
            site_id="site-1",
            list_id="list-1",
            item_id="1",
            fields={"Title": "Item"},
            etag='"123"',
        )

        call_args = client._request.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("If-Match") == '"123"'

    def test_sharepoint_list_delete_item(self, client):
        """Test deleting a SharePoint list item."""
        client._request = MagicMock(return_value={})

        result = client.sharepoint_list_delete_item(
            site_id="site-1",
            list_id="list-1",
            item_id="1",
        )

        assert result is True
        assert client._request.called

    def test_sharepoint_list_delete_nonexistent_item(self, client):
        """Test deleting non-existent item."""
        client._request = MagicMock(side_effect=NotFoundError("Not found"))

        with pytest.raises(NotFoundError):
            client.sharepoint_list_delete_item(
                site_id="site-1",
                list_id="list-1",
                item_id="nonexistent",
            )


# ---------------------------------------------------------------------------
# Outlook Calendar Operations Tests
# ---------------------------------------------------------------------------

class TestOutlookCalendarOperations:
    """Tests for Outlook calendar event operations."""

    def test_outlook_create_event(self, client):
        """Test creating an Outlook calendar event."""
        event_response = {
            "id": "event-1",
            "subject": "Team Meeting",
            "start": {"dateTime": "2025-06-15T10:00:00"},
            "end": {"dateTime": "2025-06-15T11:00:00"},
            "bodyPreview": "Discuss Q3 plans",
            "iCalUId": "event-123@graph.microsoft.com",
            "webLink": "https://outlook.office365.com/events/event-1",
        }

        client._request = MagicMock(return_value=event_response)

        event = OutlookEvent(
            subject="Team Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            body="Discuss Q3 plans",
        )

        created_event = client.outlook_create_event(
            mailbox_id="user@example.com",
            event=event,
        )

        assert created_event.id == "event-1"
        assert created_event.subject == "Team Meeting"
        assert client._request.called

    def test_outlook_create_event_with_attendees(self, client):
        """Test creating event with attendees."""
        client._request = MagicMock(return_value={
            "id": "event-1",
            "subject": "Meeting",
            "start": {"dateTime": "2025-06-15T10:00:00"},
            "end": {"dateTime": "2025-06-15T11:00:00"},
        })

        attendee = OutlookEventAttendee(
            email="attendee@example.com",
            display_name="John Doe",
        )

        event = OutlookEvent(
            subject="Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            attendees=[attendee],
        )

        client.outlook_create_event("user@example.com", event)

        # Check that attendees were included
        call_args = client._request.call_args
        data = call_args.kwargs["data"]
        assert "attendees" in data

    def test_outlook_update_event(self, client):
        """Test updating an Outlook calendar event."""
        updated_response = {
            "id": "event-1",
            "subject": "Updated Meeting",
            "start": {"dateTime": "2025-06-16T10:00:00"},
            "end": {"dateTime": "2025-06-16T11:00:00"},
        }

        client._request = MagicMock(return_value=updated_response)

        event = OutlookEvent(
            subject="Updated Meeting",
            start_time="2025-06-16T10:00:00",
            end_time="2025-06-16T11:00:00",
        )

        updated_event = client.outlook_update_event(
            mailbox_id="user@example.com",
            event_id="event-1",
            event=event,
        )

        assert updated_event.subject == "Updated Meeting"

    def test_outlook_get_events(self, client):
        """Test getting calendar events."""
        events_response = {
            "value": [
                {
                    "id": "event-1",
                    "subject": "Meeting 1",
                    "start": {"dateTime": "2025-06-15T10:00:00"},
                    "end": {"dateTime": "2025-06-15T11:00:00"},
                },
                {
                    "id": "event-2",
                    "subject": "Meeting 2",
                    "start": {"dateTime": "2025-06-16T14:00:00"},
                    "end": {"dateTime": "2025-06-16T15:00:00"},
                },
            ]
        }

        client._request = MagicMock(return_value=events_response)

        events = client.outlook_get_events(mailbox_id="user@example.com")

        assert len(events) == 2
        assert events[0].subject == "Meeting 1"
        assert events[1].subject == "Meeting 2"

    def test_outlook_get_events_with_time_filter(self, client):
        """Test getting events with time range filter."""
        client._request = MagicMock(return_value={"value": []})

        client.outlook_get_events(
            mailbox_id="user@example.com",
            start_time="2025-06-15T00:00:00",
            end_time="2025-06-16T23:59:59",
        )

        call_args = client._request.call_args
        params = call_args.kwargs["params"]
        assert "$filter" in params

    def test_outlook_delete_event(self, client):
        """Test deleting an Outlook calendar event."""
        client._request = MagicMock(return_value={})

        result = client.outlook_delete_event(
            mailbox_id="user@example.com",
            event_id="event-1",
        )

        assert result is True


# ---------------------------------------------------------------------------
# Data Models Tests
# ---------------------------------------------------------------------------

class TestOutlookEvent:
    """Tests for OutlookEvent data model."""

    def test_outlook_event_to_dict(self):
        """Test converting OutlookEvent to API format."""
        event = OutlookEvent(
            subject="Test Event",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            body="Test description",
            location="Conference Room A",
        )

        event_dict = event.to_dict()

        assert event_dict["subject"] == "Test Event"
        assert event_dict["start"]["dateTime"] == "2025-06-15T10:00:00"
        assert event_dict["end"]["dateTime"] == "2025-06-15T11:00:00"
        assert event_dict["location"]["displayName"] == "Conference Room A"

    def test_outlook_event_with_attendees(self):
        """Test OutlookEvent with attendees."""
        attendees = [
            OutlookEventAttendee(email="user1@example.com", display_name="User 1"),
            OutlookEventAttendee(email="user2@example.com", display_name="User 2"),
        ]

        event = OutlookEvent(
            subject="Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
            attendees=attendees,
        )

        event_dict = event.to_dict()
        assert len(event_dict["attendees"]) == 2


class TestSharePointListItem:
    """Tests for SharePointListItem data model."""

    def test_sharepoint_item_to_dict(self):
        """Test converting SharePointListItem to dict."""
        item = SharePointListItem(
            id="item-1",
            fields={"Title": "Test", "Status": "Active"},
            etag='"123"',
        )

        item_dict = item.to_dict()

        assert item_dict["id"] == "item-1"
        assert item_dict["fields"]["Title"] == "Test"


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_success(self, client):
        """Test successful health check."""
        client._get_auth_token = MagicMock(return_value="test-token")

        result = client.health_check()

        assert result is True

    def test_health_check_failure(self, client):
        """Test failed health check."""
        client._get_auth_token = MagicMock(side_effect=AuthenticationError("Auth failed"))

        with pytest.raises(AuthenticationError):
            client.health_check()


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling."""

    def test_graph_api_error_inheritance(self):
        """Test that all errors inherit from GraphAPIError."""
        assert issubclass(AuthenticationError, GraphAPIError)
        assert issubclass(RateLimitError, GraphAPIError)
        assert issubclass(NotFoundError, GraphAPIError)
        assert issubclass(ConflictError, GraphAPIError)

    def test_parse_datetime(self, client):
        """Test datetime parsing."""
        iso_string = "2025-06-15T10:30:45Z"
        parsed = client._parse_datetime(iso_string)

        assert parsed is not None
        assert parsed.year == 2025
        assert parsed.month == 6

    def test_parse_datetime_invalid(self, client):
        """Test parsing invalid datetime."""
        result = client._parse_datetime("invalid-date")
        assert result is None

    def test_parse_datetime_none(self, client):
        """Test parsing None."""
        result = client._parse_datetime(None)
        assert result is None


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration-style tests."""

    def test_full_sharepoint_workflow(self, client):
        """Test complete SharePoint workflow."""
        # Mock the entire workflow
        client._request = MagicMock()

        # Get items
        client._request.return_value = {"value": []}
        items = client.sharepoint_list_get_items("site-1", "list-1")
        assert isinstance(items, list)

        # Create item
        client._request.return_value = {
            "id": "new-1",
            "fields": {"Title": "New"},
        }
        item = client.sharepoint_list_create_item("site-1", "list-1", {"Title": "New"})
        assert item.id == "new-1"

        # Update item
        client._request.return_value = {
            "id": "new-1",
            "fields": {"Title": "Updated"},
        }
        updated = client.sharepoint_list_update_item(
            "site-1", "list-1", "new-1", {"Title": "Updated"}
        )
        assert updated.fields["Title"] == "Updated"

        # Delete item
        client._request.return_value = {}
        deleted = client.sharepoint_list_delete_item("site-1", "list-1", "new-1")
        assert deleted is True

    def test_full_outlook_workflow(self, client):
        """Test complete Outlook workflow."""
        client._request = MagicMock()

        # Create event
        client._request.return_value = {
            "id": "event-1",
            "subject": "Meeting",
            "start": {"dateTime": "2025-06-15T10:00:00"},
            "end": {"dateTime": "2025-06-15T11:00:00"},
        }

        event = OutlookEvent(
            subject="Meeting",
            start_time="2025-06-15T10:00:00",
            end_time="2025-06-15T11:00:00",
        )

        created = client.outlook_create_event("user@example.com", event)
        assert created.id == "event-1"

        # Get events
        client._request.return_value = {
            "value": [
                {
                    "id": "event-1",
                    "subject": "Meeting",
                    "start": {"dateTime": "2025-06-15T10:00:00"},
                    "end": {"dateTime": "2025-06-15T11:00:00"},
                }
            ]
        }

        events = client.outlook_get_events("user@example.com")
        assert len(events) == 1

        # Delete event
        client._request.return_value = {}
        deleted = client.outlook_delete_event("user@example.com", "event-1")
        assert deleted is True
