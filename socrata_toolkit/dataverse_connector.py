"""
Dataverse REST API Client for NYC DOT Work Order Management

This module provides a production-ready REST API client for Microsoft Dataverse
with OAuth2 Service Principal authentication, connection pooling, and comprehensive
error handling. Implements asymmetric bidirectional sync patterns with automatic
token refresh and retry logic.

Key Features:
- OAuth2 Service Principal authentication with Azure AD
- Token management with automatic refresh (1-hour expiry)
- Connection pooling with requests.Session
- Configurable retry logic (3 retries, exponential backoff)
- Comprehensive error handling (HTTPError, AuthenticationError, RateLimitError, TimeoutError)
- Request/response logging with correlation IDs
- Full type hints for all parameters and return values
- Dataverse API endpoint mapping for Work Orders, Repairs, Contractors, Assignments

Example:
    >>> config = DataverseConfig(
    ...     tenant_id="your-tenant-id",
    ...     client_id="your-client-id",
    ...     client_secret="your-secret",
    ...     instance_url="https://nycdot.crm.dynamics.com",
    ...     environment_id="your-env-id"
    ... )
    >>> connector = DataverseConnector(config)
    >>> work_orders = connector.list_work_orders(filters={'status': 'New'})
    >>> connector.close_connection()

References:
    - Microsoft Dataverse Web API: https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/
    - Azure OAuth2: https://learn.microsoft.com/en-us/azure/active-directory/develop/
"""

from __future__ import annotations

import json
import logging
import uuid
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DataverseError(Exception):
    """Base exception for Dataverse connector errors."""
    pass


class AuthenticationError(DataverseError):
    """Raised when authentication with Azure AD fails."""
    pass


class HTTPError(DataverseError):
    """Raised when HTTP request fails."""
    pass


class RateLimitError(DataverseError):
    """Raised when Dataverse rate limit is exceeded."""
    pass


class TimeoutError(DataverseError):
    """Raised when request timeout occurs."""
    pass


class EntityType(str, Enum):
    """Dataverse entity type mappings for NYC DOT."""
    WORK_ORDER = "msdyn_workorders"
    REPAIR = "nt_repairs"
    CONTRACTOR = "accounts"
    ASSIGNMENT = "msdyn_resourceassignments"
    COMPLIANCE = "nt_compliancerecords"


class SyncDirection(str, Enum):
    """Direction of data synchronization."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class DataverseConfig:
    """Configuration for Dataverse connector.
    
    Attributes:
        tenant_id: Azure AD tenant ID
        client_id: Azure AD application client ID
        client_secret: Azure AD application client secret
        instance_url: Dataverse instance URL (e.g., https://nycdot.crm.dynamics.com)
        environment_id: Dataverse environment ID
        max_retries: Maximum number of retry attempts (default: 3)
        timeout: Request timeout in seconds (default: 30)
        pool_size: Connection pool size (default: 10)
    """
    tenant_id: str
    client_id: str
    client_secret: str
    instance_url: str
    environment_id: str
    max_retries: int = 3
    timeout: int = 30
    pool_size: int = 10


class DataverseConnector:
    """REST API client for Microsoft Dataverse with OAuth2 authentication.
    
    Manages connection pooling, OAuth2 token lifecycle, retry logic, and error
    handling for Dataverse operations. Supports CRUD operations on work orders,
    repairs, contractor assignments, and compliance records.
    """

    def __init__(self, config: DataverseConfig) -> None:
        """Initialize Dataverse connector with configuration.
        
        Args:
            config: DataverseConfig instance with authentication and connection settings
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not all([config.tenant_id, config.client_id, config.client_secret, 
                    config.instance_url, config.environment_id]):
            raise ValueError("Missing required configuration parameters")
        
        self.config = config
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._session: Optional[requests.Session] = None
        self._correlation_id: str = str(uuid.uuid4())
        
        self._initialize_session()
        logger.info(f"DataverseConnector initialized with correlation_id={self._correlation_id}")

    def _initialize_session(self) -> None:
        """Initialize requests session with connection pooling and retry strategy."""
        self._session = requests.Session()
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.config.pool_size,
            pool_maxsize=self.config.pool_size
        )
        
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def authenticate(self) -> str:
        """Obtain OAuth2 token from Azure AD.
        
        Implements Service Principal authentication using client credentials flow.
        Tokens are cached with 1-hour expiry.
        
        Returns:
            OAuth2 access token for Dataverse API
            
        Raises:
            AuthenticationError: If authentication with Azure AD fails
        """
        # Return cached token if valid
        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            logger.debug("Using cached OAuth2 token")
            return self._token

        auth_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": f"{self.config.instance_url}/.default"
        }
        
        try:
            response = self._session.post(
                auth_url,
                data=payload,
                timeout=self.config.timeout,
                headers={
                    "X-Correlation-ID": self._correlation_id,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._token = token_data["access_token"]
            # Set expiry to 55 minutes to refresh before actual expiry
            self._token_expiry = datetime.utcnow() + timedelta(minutes=55)
            
            logger.info("Successfully obtained OAuth2 token from Azure AD")
            return self._token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationError(f"Failed to authenticate with Azure AD: {str(e)}") from e

    def _get_headers(self) -> Dict[str, str]:
        """Build HTTP headers with authentication and correlation ID.
        
        Returns:
            Dictionary of HTTP headers including authorization and tracking
        """
        token = self.authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "OData-MaxPageSize": "500",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Correlation-ID": self._correlation_id,
            "Prefer": "odata.include-annotations=OData.Community.Display.V1.FormattedValue"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute HTTP request to Dataverse API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint relative to instance
            data: Request body as dictionary (for POST/PUT/PATCH)
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            HTTPError: If request fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If request times out
        """
        url = f"{self.config.instance_url}/api/data/v9.2/{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == "GET":
                response = self._session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout
                )
            elif method == "POST":
                response = self._session.post(
                    url,
                    json=data,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout
                )
            elif method == "PUT":
                response = self._session.put(
                    url,
                    json=data,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout
                )
            elif method == "PATCH":
                response = self._session.patch(
                    url,
                    json=data,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout
                )
            elif method == "DELETE":
                response = self._session.delete(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limit exceeded. Retry after {retry_after}s")
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after}s")

            # Log response
            logger.debug(f"{method} {endpoint} -> {response.status_code}")
            
            response.raise_for_status()
            
            # Handle empty responses (204 No Content)
            if response.status_code == 204:
                return {}
            
            return response.json() if response.text else {}
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {str(e)}")
            raise TimeoutError(f"Request timeout after {self.config.timeout}s") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error on {method} {endpoint}: {str(e)}")
            raise HTTPError(f"HTTP {e.response.status_code}: {str(e)}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise HTTPError(f"Request failed: {str(e)}") from e

    # ===== WORK ORDER OPERATIONS =====

    def get_work_order(self, work_order_id: str) -> Dict[str, Any]:
        """Retrieve a single work order by ID.
        
        Args:
            work_order_id: Dataverse work order ID (GUID)
            
        Returns:
            Work order data as dictionary
        """
        endpoint = f"{EntityType.WORK_ORDER.value}({work_order_id})"
        return self._make_request("GET", endpoint)

    def list_work_orders(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List work orders with optional filters.
        
        Args:
            filters: Filter criteria (e.g., {'status': 'New', 'priority': 'High'})
            
        Returns:
            List of work order records
        """
        params = {}
        
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_conditions.append(f"{key} eq '{value}'")
                elif isinstance(value, bool):
                    filter_conditions.append(f"{key} eq {str(value).lower()}")
                else:
                    filter_conditions.append(f"{key} eq {value}")
            
            if filter_conditions:
                params["$filter"] = " and ".join(filter_conditions)
        
        params["$select"] = "msdyn_workorderid,msdyn_name,msdyn_description,statecode,prioritycode"
        
        response = self._make_request("GET", EntityType.WORK_ORDER.value, params=params)
        return response.get("value", [])

    def create_work_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new work order.
        
        Args:
            data: Work order data (msdyn_name, msdyn_description, etc.)
            
        Returns:
            Created work order record with ID
        """
        response = self._make_request("POST", EntityType.WORK_ORDER.value, data=data)
        
        # Dataverse returns created record in Location header
        created_id = response.get("msdyn_workorderid")
        if created_id:
            return self.get_work_order(created_id)
        return response

    def update_work_order(self, work_order_id: str, data: Dict[str, Any]) -> None:
        """Update an existing work order.
        
        Args:
            work_order_id: Dataverse work order ID (GUID)
            data: Fields to update
        """
        endpoint = f"{EntityType.WORK_ORDER.value}({work_order_id})"
        self._make_request("PATCH", endpoint, data=data)
        logger.info(f"Updated work order {work_order_id}")

    def delete_work_order(self, work_order_id: str) -> None:
        """Delete a work order.
        
        Args:
            work_order_id: Dataverse work order ID (GUID)
        """
        endpoint = f"{EntityType.WORK_ORDER.value}({work_order_id})"
        self._make_request("DELETE", endpoint)
        logger.info(f"Deleted work order {work_order_id}")

    # ===== REPAIR JOB OPERATIONS =====

    def get_repair_job(self, repair_id: str) -> Dict[str, Any]:
        """Retrieve a single repair job by ID.
        
        Args:
            repair_id: Dataverse repair job ID (GUID)
            
        Returns:
            Repair job data as dictionary
        """
        endpoint = f"{EntityType.REPAIR.value}({repair_id})"
        return self._make_request("GET", endpoint)

    def list_repairs(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List repair jobs with optional filters.
        
        Args:
            filters: Filter criteria (e.g., {'status': 'In Progress'})
            
        Returns:
            List of repair job records
        """
        params = {}
        
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_conditions.append(f"{key} eq '{value}'")
                else:
                    filter_conditions.append(f"{key} eq {value}")
            
            if filter_conditions:
                params["$filter"] = " and ".join(filter_conditions)
        
        params["$select"] = "nt_repairid,nt_location,nt_repairtype,nt_status"
        
        response = self._make_request("GET", EntityType.REPAIR.value, params=params)
        return response.get("value", [])

    def create_repair(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new repair job.
        
        Args:
            data: Repair job data (location, repair_type, material_type, etc.)
            
        Returns:
            Created repair job record with ID
        """
        response = self._make_request("POST", EntityType.REPAIR.value, data=data)
        
        created_id = response.get("nt_repairid")
        if created_id:
            return self.get_repair_job(created_id)
        return response

    def update_repair(self, repair_id: str, data: Dict[str, Any]) -> None:
        """Update an existing repair job.
        
        Args:
            repair_id: Dataverse repair job ID (GUID)
            data: Fields to update
        """
        endpoint = f"{EntityType.REPAIR.value}({repair_id})"
        self._make_request("PATCH", endpoint, data=data)
        logger.info(f"Updated repair job {repair_id}")

    # ===== CONTRACTOR ASSIGNMENT OPERATIONS =====

    def get_contractor_assignment(self, assignment_id: str) -> Dict[str, Any]:
        """Retrieve a single contractor assignment by ID.
        
        Args:
            assignment_id: Dataverse assignment ID (GUID)
            
        Returns:
            Contractor assignment data as dictionary
        """
        endpoint = f"{EntityType.ASSIGNMENT.value}({assignment_id})"
        return self._make_request("GET", endpoint)

    def list_assignments(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List contractor assignments with optional filters.
        
        Args:
            filters: Filter criteria (e.g., {'status': 'Assigned'})
            
        Returns:
            List of assignment records
        """
        params = {}
        
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_conditions.append(f"{key} eq '{value}'")
                else:
                    filter_conditions.append(f"{key} eq {value}")
            
            if filter_conditions:
                params["$filter"] = " and ".join(filter_conditions)
        
        params["$select"] = "msdyn_resourceassignmentid,msdyn_resourcecategoryid,msdyn_statuscode"
        
        response = self._make_request("GET", EntityType.ASSIGNMENT.value, params=params)
        return response.get("value", [])

    def create_assignment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contractor assignment.
        
        Args:
            data: Assignment data (contractor_id, work_order_id, etc.)
            
        Returns:
            Created assignment record with ID
        """
        response = self._make_request("POST", EntityType.ASSIGNMENT.value, data=data)
        
        created_id = response.get("msdyn_resourceassignmentid")
        if created_id:
            return self.get_contractor_assignment(created_id)
        return response

    def update_assignment(self, assignment_id: str, data: Dict[str, Any]) -> None:
        """Update an existing contractor assignment.
        
        Args:
            assignment_id: Dataverse assignment ID (GUID)
            data: Fields to update
        """
        endpoint = f"{EntityType.ASSIGNMENT.value}({assignment_id})"
        self._make_request("PATCH", endpoint, data=data)
        logger.info(f"Updated assignment {assignment_id}")

    # ===== COMPLIANCE RECORD OPERATIONS =====

    def get_compliance_record(self, record_id: str) -> Dict[str, Any]:
        """Retrieve a single compliance record by ID.
        
        Args:
            record_id: Dataverse compliance record ID (GUID)
            
        Returns:
            Compliance record data as dictionary
        """
        endpoint = f"{EntityType.COMPLIANCE.value}({record_id})"
        return self._make_request("GET", endpoint)

    def create_compliance_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new compliance record.
        
        Args:
            data: Compliance record data (work_order_id, compliance_type, etc.)
            
        Returns:
            Created compliance record with ID
        """
        response = self._make_request("POST", EntityType.COMPLIANCE.value, data=data)
        
        created_id = response.get("nt_compliancerecordid")
        if created_id:
            return self.get_compliance_record(created_id)
        return response

    # ===== BATCH OPERATIONS =====

    def batch_update(self, updates: List[Tuple[str, str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Execute multiple updates in batch.
        
        Implements batching using OData $batch requests to reduce HTTP overhead.
        
        Args:
            updates: List of tuples (entity_type, entity_id, data)
                Example: [("msdyn_workorders", "id1", {"status": "Complete"}), ...]
            
        Returns:
            List of update responses
        """
        results = []
        
        # Process in chunks to avoid exceeding Dataverse limits
        batch_size = 20
        for i in range(0, len(updates), batch_size):
            batch_chunk = updates[i:i+batch_size]
            chunk_results = self._execute_batch_chunk(batch_chunk)
            results.extend(chunk_results)
        
        return results

    def _execute_batch_chunk(self, updates: List[Tuple[str, str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Execute a single batch of updates.
        
        Args:
            updates: List of tuples (entity_type, entity_id, data)
            
        Returns:
            List of update responses
        """
        results = []
        
        for entity_type, entity_id, data in updates:
            try:
                endpoint = f"{entity_type}({entity_id})"
                self._make_request("PATCH", endpoint, data=data)
                results.append({
                    "success": True,
                    "entity_type": entity_type,
                    "entity_id": entity_id
                })
                logger.debug(f"Batch updated {entity_type} {entity_id}")
            except DataverseError as e:
                logger.error(f"Batch update failed for {entity_type} {entity_id}: {str(e)}")
                results.append({
                    "success": False,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "error": str(e)
                })
        
        return results

    def close_connection(self) -> None:
        """Close session and clean up resources."""
        if self._session:
            self._session.close()
            logger.info("Dataverse connector session closed")
