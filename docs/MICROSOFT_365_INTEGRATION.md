# Microsoft 365 Integration Guide

This guide explains how to set up and use the Microsoft 365 integration in the NYC DOT Sidewalk Toolkit, including SharePoint list synchronization, Outlook calendar management, and unified OAuth2 token management.

## Table of Contents

1. [Overview](#overview)
2. [Setup Guide](#setup-guide)
3. [Authentication & Token Management](#authentication--token-management)
4. [SharePoint Sync Workflows](#sharepoint-sync-workflows)
5. [Outlook Calendar Workflows](#outlook-calendar-workflows)
6. [Real-World Examples](#real-world-examples)
7. [Error Handling & Retries](#error-handling--retries)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

## Overview

The Microsoft 365 integration provides production-grade APIs for:

- **SharePoint List Synchronization**: Bi-directional sync between Dataverse work orders and SharePoint lists with conflict detection
- **Outlook Calendar Management**: Create, update, and manage calendar events for repair work orders with attendee management
- **Unified Authentication**: OAuth2 Service Principal authentication with automatic token refresh and caching
- **Rate Limiting**: Exponential backoff retry strategy for rate-limited API calls
- **Connection Pooling**: Reusable HTTP session with configurable pool sizes
- **Observability**: Integration with metrics collection and lineage tracking

### Key Components

```
socrata_toolkit/
├── microsoft_graph.py          # GraphAPI client (650+ lines)
│   ├── GraphAPIClient          # Main client class
│   ├── SharePointListItem      # SharePoint data model
│   ├── OutlookEvent           # Calendar event model
│   ├── TokenCache             # Token caching with TTL
│   └── OAuth2 token management
│
└── work_management.py          # M365 sync adapters (350+ lines)
    ├── SharePointListSync     # Bi-directional sync
    ├── OutlookCalendarSync    # Calendar management
    ├── SyncDirection          # Sync direction enum
    └── ConflictResolutionStrategy
```

## Setup Guide

### Step 1: Azure AD App Registration

Register a new application in Azure AD to obtain OAuth2 credentials:

1. **Sign in to Azure Portal**
   - Go to https://portal.azure.com
   - Navigate to Azure AD > App registrations

2. **Create New Application**
   - Click "New registration"
   - Name: `NYC-DOT-Sidewalk-Toolkit-M365`
   - Account type: Single tenant
   - Redirect URI: Leave blank (Service Principal doesn't need this)
   - Click "Register"

3. **Record Application IDs**
   - Copy "Application (client) ID" → `GRAPH_CLIENT_ID`
   - Copy "Directory (tenant) ID" → `GRAPH_TENANT_ID`

4. **Create Client Secret**
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Description: `NYC-DOT-Toolkit-M365`
   - Expires: 12 months
   - Click "Add"
   - Copy the secret value → `GRAPH_CLIENT_SECRET`
   - ⚠️ **Save this immediately** - it's only shown once!

### Step 2: Grant API Permissions

Configure permissions for Microsoft Graph API:

1. **Add API Permissions**
   - Go to "API permissions"
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Choose "Application permissions"

2. **Select Required Permissions**
   - **SharePoint**: `Sites.ReadWrite.All`
   - **Outlook**: `Calendars.ReadWrite`, `Mail.Send`
   - **Teams**: `Channel.Create`, `TeamsAppInstallation.ReadWriteSelfForTeam`
   - Click "Add permissions"

3. **Grant Admin Consent**
   - Back in API permissions
   - Click "Grant admin consent for [Tenant]"
   - Confirm in dialog

### Step 3: Configure Environment Variables

Set credentials in your environment:

```bash
# .env file or environment variables
export GRAPH_TENANT_ID="your-tenant-id"
export GRAPH_CLIENT_ID="your-client-id"
export GRAPH_CLIENT_SECRET="your-client-secret"

# Optional configuration
export GRAPH_API_BASE_URL="https://graph.microsoft.com/v1.0"
export GRAPH_API_TIMEOUT=30
export GRAPH_API_MAX_RETRIES=3
export GRAPH_RATE_LIMIT_DELAY=1.0
```

### Step 4: Identify SharePoint Site & List IDs

Find the IDs for your target SharePoint site and list:

```python
from socrata_toolkit.microsoft_graph import GraphAPIClient, GraphAPIConfig

config = GraphAPIConfig(
    tenant_id=os.getenv("GRAPH_TENANT_ID"),
    client_id=os.getenv("GRAPH_CLIENT_ID"),
    client_secret=os.getenv("GRAPH_CLIENT_SECRET"),
)

client = GraphAPIClient(config)

# List all SharePoint sites
sites = client._request("GET", "sites?search=*")

# Once you have site_id, list its lists
lists = client._request("GET", f"sites/{site_id}/lists")

# Copy site_id and list_id for use in sync configuration
print(f"Site ID: {site_id}")
print(f"List ID: {list_id}")

client.close()
```

### Step 5: Verify Setup

Test the connection:

```python
from socrata_toolkit.microsoft_graph import GraphAPIConfig, GraphAPIClient

config = GraphAPIConfig(
    tenant_id=os.getenv("GRAPH_TENANT_ID"),
    client_id=os.getenv("GRAPH_CLIENT_ID"),
    client_secret=os.getenv("GRAPH_CLIENT_SECRET"),
)

client = GraphAPIClient(config)

# This will authenticate and perform a test request
if client.health_check():
    print("✓ Authentication successful!")
else:
    print("✗ Authentication failed!")

client.close()
```

## Authentication & Token Management

### Token Lifecycle

The GraphAPI client handles OAuth2 token management automatically:

```
1. Request needs authentication
   ↓
2. Check token cache
   ├─ Valid? → Use cached token → Request
   └─ Invalid/Expired? → Continue
3. Request new token from Azure AD
4. Cache token (TTL: 55 minutes)
5. Use token in request
```

### Token Caching

Tokens are cached with automatic expiry:

```python
from socrata_toolkit.microsoft_graph import TokenCache, OAuthToken
from datetime import timedelta, timezone, datetime

cache = TokenCache(ttl_seconds=3300)  # 55 minutes

# Token automatically expires when:
# 1. Cache TTL expires (55 minutes)
# 2. Token's expires_in passes (60 minutes)
# 3. Either condition is met - whichever comes first

token = OAuthToken(
    access_token="token-string",
    expires_in=3600,  # Expires in 60 minutes
)

cache.set(token)
cached = cache.get()  # Returns token if valid
```

### Automatic Token Refresh

Tokens are automatically refreshed before expiry:

```python
client = GraphAPIClient(config)

# First call - gets new token
result1 = client._request("GET", "me")  # → Acquires token

# Second call within 55 minutes - uses cached token
result2 = client._request("GET", "me")  # → Uses cached token

# Call after 55 minutes - gets new token
result3 = client._request("GET", "me")  # → Acquires new token
```

### Token Expiry Buffer

The client includes a 60-second buffer to avoid using almost-expired tokens:

```python
# If token expires at: 2025-06-15 10:00:00 UTC
# Considered expired at: 2025-06-15 09:59:00 UTC (60s before)
# This prevents "token near expiry" errors
```

## SharePoint Sync Workflows

### Basic SharePoint Operations

#### Get List Items

```python
from socrata_toolkit.microsoft_graph import GraphAPIClient, GraphAPIConfig

config = GraphAPIConfig(...)
client = GraphAPIClient(config)

# Get all items from a list
items = client.sharepoint_list_get_items(
    site_id="site-123",
    list_id="list-456",
)

# Get items with filtering
items = client.sharepoint_list_get_items(
    site_id="site-123",
    list_id="list-456",
    filters={
        "Status": "Active",
        "Priority": 1,
    },
)

# Get items with pagination
items = client.sharepoint_list_get_items(
    site_id="site-123",
    list_id="list-456",
    top=50,
    skip=100,  # Skip first 100 items
)

# Get specific fields only
items = client.sharepoint_list_get_items(
    site_id="site-123",
    list_id="list-456",
    select_fields=["Title", "Status", "Location"],
)

client.close()
```

#### Create List Item

```python
item = client.sharepoint_list_create_item(
    site_id="site-123",
    list_id="list-456",
    fields={
        "Title": "Pothole Repair - Broadway & 42nd",
        "Status": "Active",
        "Location": "Broadway & 42nd St",
        "Priority": 1,
        "Description": "Emergency pothole repair",
    }
)

print(f"Created item: {item.id}")
print(f"Web URL: {item.webUrl}")
```

#### Update List Item

```python
updated_item = client.sharepoint_list_update_item(
    site_id="site-123",
    list_id="list-456",
    item_id="item-789",
    fields={
        "Status": "Complete",
        "CompletionDate": "2025-06-15",
    },
    etag='"123abc"',  # Optional: for optimistic concurrency
)
```

#### Delete List Item

```python
success = client.sharepoint_list_delete_item(
    site_id="site-123",
    list_id="list-456",
    item_id="item-789",
)
```

### Bi-Directional Sync with Conflict Detection

```python
from socrata_toolkit.work_management import (
    SharePointListSync,
    SyncDirection,
    ConflictResolutionStrategy,
)
import pandas as pd

# Create sync instance
sync = SharePointListSync(
    site_id="site-123",
    list_id="list-456",
    mapping={
        "Id": "ExternalId",
        "Title": "Title",
        "Status": "Status",
        "Location": "Location",
        "ModifiedOn": "LastModified",
    },
    graph_client=client,
)

# Load Dataverse records
df = pd.read_csv("work_orders.csv")

# Sync to SharePoint
created, updated, conflicts = sync.sync_from_dataverse(
    df,
    id_column="Id",
    modified_column="ModifiedOn",
    direction=SyncDirection.UPSTREAM,
    conflict_strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
)

print(f"Created: {created}, Updated: {updated}, Conflicts: {len(conflicts)}")

# Review conflicts
for conflict in conflicts:
    print(f"Conflict in {conflict['local_id']}:")
    print(f"  Local modified: {conflict['local_modified']}")
    print(f"  Remote modified: {conflict['remote_modified']}")

# Get sync history
history = sync.get_sync_history()
for record in history:
    print(f"Sync at {record['timestamp']}: {record['created']} created, {record['updated']} updated")
```

### Conflict Resolution Strategies

```python
from socrata_toolkit.work_management import ConflictResolutionStrategy

# MANUAL_REVIEW: Don't update if both changed since last sync
sync.sync_from_dataverse(
    df,
    conflict_strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
)

# SOURCE_WINS: Local data overwrites remote
sync.sync_from_dataverse(
    df,
    conflict_strategy=ConflictResolutionStrategy.SOURCE_WINS,
)

# TARGET_WINS: Remote data takes precedence
sync.sync_from_dataverse(
    df,
    conflict_strategy=ConflictResolutionStrategy.TARGET_WINS,
)

# LAST_WRITE_WINS: Whoever was modified most recently wins
sync.sync_from_dataverse(
    df,
    conflict_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
)
```

## Outlook Calendar Workflows

### Create Calendar Events

```python
from socrata_toolkit.work_management import OutlookCalendarSync
from socrata_toolkit.microsoft_graph import OutlookEvent, OutlookEventAttendee

sync = OutlookCalendarSync(
    supervisor_mailbox="supervisor@org.onmicrosoft.com",
    contractor_mailbox="contractor@org.onmicrosoft.com",
    graph_client=client,
)

# Create event for a repair work order
event_id, success = sync.create_repair_event(
    work_order_id="WO-001",
    title="Pothole Repair - Broadway & 42nd",
    start_time="2025-06-15T09:00:00",
    end_time="2025-06-15T17:00:00",
    location="Broadway & 42nd St, Manhattan",
    description="Emergency pothole repair. Supervisor approval required.",
    attendees=["field-supervisor@org.com", "contractor@org.com"],
)

if success:
    print(f"Created event: {event_id}")
else:
    print("Failed to create event")
```

### Update Calendar Events

```python
# Reschedule event
success = sync.update_repair_event(
    work_order_id="WO-001",
    start_time="2025-06-16T09:00:00",
    end_time="2025-06-16T17:00:00",
)

# Update status
success = sync.update_repair_event(
    work_order_id="WO-001",
    status="In Progress",
)

# Get sync history
history = sync.get_sync_history()
for record in history:
    print(f"{record['action']} event for {record['work_order_id']} at {record['timestamp']}")
```

### Direct Outlook API Operations

```python
from socrata_toolkit.microsoft_graph import OutlookEvent, OutlookEventAttendee

# Create attendees
attendees = [
    OutlookEventAttendee(
        email="supervisor@org.com",
        display_name="Field Supervisor",
    ),
    OutlookEventAttendee(
        email="contractor@org.com",
        display_name="Contractor",
    ),
]

# Create event
event = OutlookEvent(
    subject="Sidewalk Repair Meeting",
    start_time="2025-06-15T10:00:00",
    end_time="2025-06-15T11:00:00",
    body="Discuss repair scope and timeline",
    location="DOT Office - Conference Room A",
    attendees=attendees,
    is_reminder_on=True,
    reminder_minutes_before_start=30,
)

created_event = client.outlook_create_event(
    mailbox_id="supervisor@org.onmicrosoft.com",
    event=event,
)

# Get events
events = client.outlook_get_events(
    mailbox_id="supervisor@org.onmicrosoft.com",
    start_time="2025-06-01T00:00:00",
    end_time="2025-06-30T23:59:59",
)

# Update event
event.subject = "Updated Meeting Title"
updated = client.outlook_update_event(
    mailbox_id="supervisor@org.onmicrosoft.com",
    event_id=created_event.id,
    event=event,
)

# Delete event
deleted = client.outlook_delete_event(
    mailbox_id="supervisor@org.onmicrosoft.com",
    event_id=created_event.id,
)
```

## Real-World Examples

### Example 1: Work Order → SharePoint → Outlook → Teams

This example shows a complete workflow from Dataverse work order creation to SharePoint and calendar invites:

```python
from socrata_toolkit.microsoft_graph import GraphAPIClient, GraphAPIConfig
from socrata_toolkit.work_management import (
    SharePointListSync,
    OutlookCalendarSync,
)
from socrata_toolkit.dataverse_connector import DataverseConnector
import pandas as pd

# Initialize clients
graph_config = GraphAPIConfig(
    tenant_id=os.getenv("GRAPH_TENANT_ID"),
    client_id=os.getenv("GRAPH_CLIENT_ID"),
    client_secret=os.getenv("GRAPH_CLIENT_SECRET"),
)
graph_client = GraphAPIClient(graph_config)

# Step 1: Get work orders from Dataverse
dv = DataverseConnector(...)
work_orders = dv.list_work_orders(filters={"status": "New"})
df = pd.DataFrame(work_orders)

# Step 2: Sync to SharePoint
sharepoint_sync = SharePointListSync(
    site_id="site-123",
    list_id="list-456",
    mapping={
        "Id": "ExternalId",
        "Title": "Title",
        "Location": "Location",
        "Status": "Status",
        "EstimatedCost": "EstimatedCost",
    },
    graph_client=graph_client,
)

created, updated, conflicts = sharepoint_sync.sync_from_dataverse(
    df,
    id_column="Id",
)
print(f"Synced to SharePoint: {created} created, {updated} updated")

# Step 3: Create Outlook calendar events
outlook_sync = OutlookCalendarSync(
    supervisor_mailbox="supervisor@org.onmicrosoft.com",
    contractor_mailbox="contractor@org.onmicrosoft.com",
    graph_client=graph_client,
)

for _, row in df.iterrows():
    event_id, success = outlook_sync.create_repair_event(
        work_order_id=row["Id"],
        title=f"Repair: {row['Title']}",
        start_time=row["ScheduledStartTime"],
        end_time=row["ScheduledEndTime"],
        location=row["Location"],
        description=f"Work Order: {row['Id']}\n{row['Description']}",
    )
    if success:
        print(f"Created calendar event {event_id} for {row['Id']}")

# Step 4: Send Teams notification (using existing Teams integration)
from socrata_toolkit.work_management import M365Adapter

for _, row in df.iterrows():
    notification = M365Adapter.teams_notification(
        title=f"New Work Order: {row['Title']}",
        body=f"Location: {row['Location']}\nStatus: {row['Status']}",
        facts={
            "Priority": row.get("Priority", "Normal"),
            "EstimatedCost": f"${row.get('EstimatedCost', 0):,.2f}",
            "Supervisor": "Field Team",
        },
    )
    # Send notification to Teams webhook
    # webhook.send(notification)

graph_client.close()
```

### Example 2: Conflict Detection & Manual Review

```python
from socrata_toolkit.work_management import (
    SharePointListSync,
    ConflictResolutionStrategy,
)

sync = SharePointListSync(...)

created, updated, conflicts = sync.sync_from_dataverse(
    df,
    conflict_strategy=ConflictResolutionStrategy.MANUAL_REVIEW,
)

if conflicts:
    print(f"⚠️ {len(conflicts)} conflicts detected - manual review required\n")
    
    for conflict in conflicts:
        print(f"Work Order: {conflict['local_id']}")
        print(f"  Local modified:  {conflict['local_modified']}")
        print(f"  Remote modified: {conflict['remote_modified']}")
        print(f"  → Requires manual resolution\n")
    
    # Send alert to Teams for manual review
    send_alert_to_teams(
        title="M365 Sync Conflicts Detected",
        body=f"{len(conflicts)} conflicts require manual review",
        facts={
            "Affected Items": len(conflicts),
            "Action Required": "Review in SharePoint",
        },
    )
```

### Example 3: Event Rescheduling

```python
# When a work order is rescheduled in Dataverse
def handle_work_order_reschedule(work_order_id, new_start, new_end):
    outlook_sync = OutlookCalendarSync(...)
    
    success = outlook_sync.update_repair_event(
        work_order_id=work_order_id,
        start_time=new_start,
        end_time=new_end,
    )
    
    if success:
        print(f"Rescheduled event for {work_order_id}")
    else:
        print(f"Failed to reschedule event for {work_order_id}")
```

## Error Handling & Retries

### Rate Limiting

The client automatically handles rate limits with exponential backoff:

```python
# Automatic retry with backoff
# Attempt 1: Fails with 429
# → Wait: 1.0 second
# Attempt 2: Fails with 429
# → Wait: 2.0 seconds
# Attempt 3: Fails with 429
# → Wait: 4.0 seconds
# Attempt 4: Succeeds

# Configure backoff behavior
config = GraphAPIConfig(
    ...,
    max_retries=5,
    rate_limit_delay=0.5,  # Initial delay
    backoff_factor=2.0,     # Exponential multiplier
)
```

### Error Handling

```python
from socrata_toolkit.microsoft_graph import (
    GraphAPIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ConflictError,
    TimeoutError,
)

try:
    item = client.sharepoint_list_create_item(
        site_id="site-123",
        list_id="list-456",
        fields={...},
    )
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Likely credential issue
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Wait and retry manually
except NotFoundError as e:
    print(f"Resource not found: {e}")
    # Check site_id, list_id, or item_id
except ConflictError as e:
    print(f"Conflict detected: {e}")
    # Handle concurrent modification
except TimeoutError as e:
    print(f"Request timed out: {e}")
    # Network issue, retry
except GraphAPIError as e:
    print(f"API error: {e}")
    # Generic Graph API error
```

## Troubleshooting

### Issue: Authentication Fails

```
Error: "Failed to acquire access token"
```

**Solutions:**
1. Verify credentials are correct:
   ```bash
   echo $GRAPH_TENANT_ID
   echo $GRAPH_CLIENT_ID
   echo $GRAPH_CLIENT_SECRET
   ```

2. Check app registration permissions:
   - Go to Azure Portal > App registrations > Your app
   - Verify "API permissions" includes required permissions
   - Click "Grant admin consent"

3. Verify tenant ID:
   ```bash
   # Should show your tenant domain
   curl https://login.microsoftonline.com/{TENANT_ID}/.well-known/openid-configuration
   ```

### Issue: SharePoint List Not Found

```
Error: "Resource not found: sites/{site_id}/lists/{list_id}"
```

**Solutions:**
1. Get correct site and list IDs:
   ```python
   # List available sites
   sites = client._request("GET", "sites?search=*")
   for site in sites["value"]:
       print(f"Site: {site['id']} - {site['name']}")
   
   # List available lists for a site
   lists = client._request("GET", f"sites/{site_id}/lists")
   for list_item in lists["value"]:
       print(f"List: {list_item['id']} - {list_item['name']}")
   ```

2. Verify site URL contains the domain:
   ```python
   # Correct
   site_id = "tenant.sharepoint.com,site-guid,web-guid"
   
   # Incorrect
   site_id = "site-guid"
   ```

### Issue: Outlook Calendar Not Accessible

```
Error: "Mail.Send" or "Calendars.ReadWrite" permission error
```

**Solutions:**
1. Verify API permissions in Azure AD:
   - Go to "API permissions"
   - Ensure `Calendars.ReadWrite` is granted

2. Verify mailbox address format:
   ```python
   # Correct formats
   mailbox_id = "user@org.onmicrosoft.com"
   mailbox_id = "user@company.com"
   ```

### Issue: Sync Taking Too Long

```
Large dataset sync is slow
```

**Solutions:**
1. Use pagination:
   ```python
   for offset in range(0, total_items, 100):
       items = client.sharepoint_list_get_items(
           site_id=site_id,
           list_id=list_id,
           top=100,
           skip=offset,
       )
   ```

2. Filter data before syncing:
   ```python
   # Only sync modified items
   recent_df = df[df["ModifiedOn"] > last_sync_time]
   sync.sync_from_dataverse(recent_df)
   ```

3. Increase connection pool size:
   ```python
   config = GraphAPIConfig(...)
   # Pool settings are configured in _create_session()
   # Default: pool_connections=10, pool_maxsize=20
   ```

## API Reference

### GraphAPIClient Methods

#### SharePoint Operations

- `sharepoint_list_get_items(site_id, list_id, filters, select_fields, top, skip)` → `List[SharePointListItem]`
- `sharepoint_list_create_item(site_id, list_id, fields)` → `SharePointListItem`
- `sharepoint_list_update_item(site_id, list_id, item_id, fields, etag)` → `SharePointListItem`
- `sharepoint_list_delete_item(site_id, list_id, item_id)` → `bool`

#### Outlook Operations

- `outlook_create_event(mailbox_id, event)` → `OutlookEvent`
- `outlook_update_event(mailbox_id, event_id, event)` → `OutlookEvent`
- `outlook_get_events(mailbox_id, start_time, end_time)` → `List[OutlookEvent]`
- `outlook_delete_event(mailbox_id, event_id)` → `bool`

#### Health & Lifecycle

- `health_check()` → `bool`
- `close()` → `None`
- `__enter__()` / `__exit__()` → Context manager support

### SharePointListSync Methods

- `sync_from_dataverse(df, id_column, modified_column, direction, conflict_strategy)` → `Tuple[int, int, List]`
- `get_conflicts()` → `List[Dict]`
- `get_sync_history()` → `List[Dict]`

### OutlookCalendarSync Methods

- `create_repair_event(work_order_id, title, start_time, end_time, location, description, attendees)` → `Tuple[str, bool]`
- `update_repair_event(work_order_id, start_time, end_time, location, status)` → `bool`
- `get_sync_history()` → `List[Dict]`

## Integration with Existing Toolkit

### Lineage Tracking

```python
from socrata_toolkit.lineage_core import DAG, TransformationNode, NodeType

# Tag M365 operations for lineage tracking
dag = DAG()

m365_sync_node = TransformationNode(
    node_id="m365_sharepoint_sync",
    name="Dataverse → SharePoint Sync",
    node_type=NodeType.SINK,  # SharePoint is a sink
    owner="platform-team",
)
dag.add_node(m365_sync_node)
```

### Observability Metrics

```python
from socrata_toolkit.observability_metrics import MetricsCollector

# Metrics are automatically collected
# - graph_api_request_latency_ms
# - graph_api_http_*
# - sharepoint_list_get_latency_ms
# - sharepoint_items_created / updated / deleted
# - outlook_event_create_latency_ms
# - outlook_events_created / updated / deleted
# - sharepoint_sync_latency_ms
# - sharepoint_sync_conflicts
```

## Support & Feedback

For issues or questions:
1. Check the troubleshooting section above
2. Review test files for usage examples
3. Check application logs for detailed error messages
4. Contact the platform team
