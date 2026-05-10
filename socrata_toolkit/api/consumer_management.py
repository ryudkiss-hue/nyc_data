"""API Consumer Management Module

Manages external API consumers (organizations using the API).

Features:
    - Consumer registration and lifecycle
    - API key issuance and rotation
    - Usage tracking and billing
    - Rate limit tiers and upgrades
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import secrets

logger = logging.getLogger(__name__)


class ConsumerStatus(str, Enum):
    """Consumer status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass
class APIConsumer:
    """External API consumer."""

    consumer_id: str
    name: str
    contact_email: str
    contact_name: str = ""
    organization: str = ""
    status: ConsumerStatus = ConsumerStatus.ACTIVE
    quota_tier: str = "standard"
    api_keys: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    usage_this_month: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


class APIConsumerManager:
    """Manages API consumers."""

    def __init__(self, db_connection: Optional[object] = None) -> None:
        """Initialize consumer manager."""
        self.db = db_connection
        self._consumers: Dict[str, APIConsumer] = {}

    def create_consumer(
        self,
        name: str,
        contact_email: str,
        contact_name: str = "",
        organization: str = "",
    ) -> APIConsumer:
        """Create new API consumer."""
        consumer_id = secrets.token_hex(8)
        consumer = APIConsumer(
            consumer_id=consumer_id,
            name=name,
            contact_email=contact_email,
            contact_name=contact_name,
            organization=organization,
        )
        self._consumers[consumer_id] = consumer
        logger.info(f"Consumer created: {consumer_id} ({name})")
        return consumer

    def get_consumer(self, consumer_id: str) -> Optional[APIConsumer]:
        """Get consumer by ID."""
        return self._consumers.get(consumer_id)

    def list_consumers(self) -> List[APIConsumer]:
        """List all consumers."""
        return list(self._consumers.values())

    def suspend_consumer(self, consumer_id: str) -> bool:
        """Suspend consumer."""
        if consumer_id in self._consumers:
            self._consumers[consumer_id].status = ConsumerStatus.SUSPENDED
            logger.warning(f"Consumer suspended: {consumer_id}")
            return True
        return False

    def revoke_consumer(self, consumer_id: str) -> bool:
        """Revoke consumer."""
        if consumer_id in self._consumers:
            self._consumers[consumer_id].status = ConsumerStatus.REVOKED
            logger.warning(f"Consumer revoked: {consumer_id}")
            return True
        return False

    def issue_api_key(self, consumer_id: str) -> str:
        """Issue API key for consumer."""
        if consumer_id not in self._consumers:
            raise ValueError(f"Consumer {consumer_id} not found")

        api_key = f"sk_{secrets.token_hex(32)}"
        self._consumers[consumer_id].api_keys.append(api_key)
        logger.info(f"API key issued for consumer {consumer_id}")
        return api_key

    def get_usage_report(self, consumer_id: str) -> Dict:
        """Get usage report for consumer."""
        if consumer_id not in self._consumers:
            return {}

        consumer = self._consumers[consumer_id]
        return {
            "consumer_id": consumer_id,
            "name": consumer.name,
            "usage_this_month": consumer.usage_this_month,
            "quota_tier": consumer.quota_tier,
            "status": consumer.status.value,
        }
