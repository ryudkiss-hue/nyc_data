from __future__ import annotations

import hashlib
import os
import secrets
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


class AuthenticationError(Exception):
    """Exception raised for authentication failures."""

@dataclass
class User:
    user_id: str
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)

@dataclass
class AuthContext:
    principal_id: str
    user: User
    roles: list[str]
    permissions: set[str]

class JWTAuthProvider:
    def __init__(self, secret_key: str, expiry_minutes: int = 60, cache_size: int = 1000):
        self.secret_key = secret_key
        self.expiry_minutes = expiry_minutes
        self.cache_size = cache_size
        self._token_cache: OrderedDict[str, AuthContext] = OrderedDict()

    def create_token(self, user: User, expiry: timedelta | None = None) -> str:
        exp = datetime.now(timezone.utc) + (expiry if expiry is not None else timedelta(minutes=self.expiry_minutes))
        payload = {
            "sub": user.user_id,
            "email": user.email,
            "roles": user.roles,
            "exp": exp
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def authenticate(self, credentials: dict[str, Any]) -> AuthContext:
        token = credentials.get("token")
        if not token:
            raise AuthenticationError("Missing token")

        if token in self._token_cache:
            self._token_cache.move_to_end(token)
            return self._token_cache[token]

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user = User(
                user_id=payload["sub"],
                email=payload.get("email", ""),
                roles=payload.get("roles", [])
            )
            context = AuthContext(
                principal_id=user.user_id,
                user=user,
                roles=user.roles,
                permissions=set()
            )

            # LRU Cache management
            if len(self._token_cache) >= self.cache_size:
                self._token_cache.popitem(last=False)
            self._token_cache[token] = context

            return context
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid signature")

class APIKeyAuthProvider:
    """
    Production-ready API Key provider that validates SHA-256 hashes of keys.
    Allowed hashes are loaded from the SOCRATA_ALLOWED_KEY_HASHES environment variable (comma-separated).
    """
    def __init__(self):
        self._allowed_hashes = self._load_allowed_keys()

    def _load_allowed_keys(self) -> set[str]:
        raw = os.getenv("SOCRATA_ALLOWED_KEY_HASHES", "")
        return {h.strip() for h in raw.split(",") if h.strip()}

    def authenticate(self, credentials: dict[str, Any]) -> AuthContext:
        key = credentials.get("api_key")
        if not key:
            raise AuthenticationError("Missing API Key")

        hashed = hash_api_key(key)
        if hashed not in self._allowed_hashes:
            raise AuthenticationError("Invalid API Key")

        return AuthContext(
            principal_id=f"api_{hashed[:8]}",
            user=User(f"api_{hashed[:8]}", "api@internal.nyc.gov", roles=["api_user"]),
            roles=["api_user"],
            permissions=set()
        )

def generate_api_key() -> str:
    return f"sk_{secrets.token_hex(32)}"

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def get_api_key_prefix(key: str) -> str:
    if len(key) < 10: return "****"
    return f"{key[:5]}****{key[-4:]}"
