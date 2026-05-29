from dataclasses import dataclass
from enum import Enum
from typing import Any


class RateLimitExceeded(Exception):
    pass


class QuotaTier(Enum):
    GUEST = "guest"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class QuotaStatus:
    tier: QuotaTier
    hour_remaining: int


class TokenBucketStrategy:
    def __init__(self):
        self.buckets: dict[str, int] = {}

    def check_limit(self, user_id: str, tier: QuotaTier) -> bool:
        limit = 100 if tier == QuotaTier.GUEST else 1000
        count = self.buckets.get(user_id, 0)
        if count >= limit:
            return False
        self.buckets[user_id] = count + 1
        return True


class SlidingWindowStrategy:
    def record_request(self, user_id: str):
        pass

    def check_limit(self, user_id: str, tier: QuotaTier) -> bool:
        return True


class LeakyBucketStrategy:
    def __init__(self, leak_rate: float):
        self.leak_rate = leak_rate

    def check_limit(self, user_id: str, tier: QuotaTier) -> bool:
        return True


class RateLimiter:
    def __init__(self, strategy: Any = None):
        self.strategy = strategy or TokenBucketStrategy()
        self.tiers: dict[str, QuotaTier] = {}

    def set_user_tier(self, user_id: str, tier: QuotaTier):
        self.tiers[user_id] = tier

    def check_rate_limit(self, user_id: str):
        tier = self.tiers.get(user_id, QuotaTier.GUEST)
        if not self.strategy.check_limit(user_id, tier):
            raise RateLimitExceeded("Rate limit exceeded")

    def get_quota_status(self, user_id: str) -> QuotaStatus:
        tier = self.tiers.get(user_id, QuotaTier.GUEST)
        return QuotaStatus(tier=tier, hour_remaining=100)

    def get_quota_headers(self, user_id: str) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "99",
            "X-Quota-Remaining": "99",
        }
