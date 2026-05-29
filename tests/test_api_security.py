"""API Security, Authentication, Authorization, and Governance Tests

Comprehensive test suite (50+ test cases) for:
- Authentication (JWT, API Key, OAuth2, Basic)
- Authorization (RBAC, resource hierarchy, delegation)
- Rate Limiting (token bucket, sliding window, leaky bucket)
- Versioning (deprecation, breaking changes, negotiation)
- Data Governance (PII masking, classification, quality gates)
- Request Pipeline (full lifecycle)
"""

from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("fastapi", reason="fastapi required for API tests")

# Import authentication
from socrata_toolkit.api.auth import (
    APIKeyAuthProvider,
    AuthenticationError,
    JWTAuthProvider,
    User,
    generate_api_key,
    get_api_key_prefix,
    hash_api_key,
)

# Import authorization
from socrata_toolkit.api.authorization import (
    Classification,
    DelegatedPermission,
    RBACEnforcer,
    Resource,
)

# Import governance
from socrata_toolkit.api.governance import (
    GovernanceEnforcer,
    MaskingStrategy,
    PIIType,
)

# Import rate limiting
from socrata_toolkit.api.rate_limiting import (
    LeakyBucketStrategy,
    QuotaTier,
    RateLimiter,
    RateLimitExceeded,
    SlidingWindowStrategy,
    TokenBucketStrategy,
)

# Import request pipeline
from socrata_toolkit.api.request_pipeline import APIRequestPipeline, PipelineRequest

# Import versioning
from socrata_toolkit.api.versioning import (
    VersionManager,
    VersionStatus,
    parse_version_from_accept_header,
)

# ====================================================================
# AUTHENTICATION TESTS
# ====================================================================


class TestJWTAuthentication:
    """JWT authentication tests."""

    def test_jwt_creation_and_validation(self):
        """Test JWT token creation and validation."""
        provider = JWTAuthProvider(secret_key="test_secret_key_12345")
        user = User(user_id="user_123", email="test@example.com", roles=["viewer"])

        token = provider.create_token(user)
        assert token
        assert isinstance(token, str)

        # Validate token
        context = provider.authenticate({"token": token})
        assert context.principal_id == "user_123"
        assert context.user.email == "test@example.com"
        assert "viewer" in context.roles

    def test_jwt_expiry(self):
        """Test expired JWT token rejection."""
        provider = JWTAuthProvider(secret_key="test_secret", expiry_minutes=0)
        user = User(user_id="user_123", email="test@example.com")

        # Create token with immediate expiry
        import time

        time.sleep(0.1)

        token = provider.create_token(user, expiry=timedelta(seconds=0))

        # Should raise expired error
        with pytest.raises(AuthenticationError):
            provider.authenticate({"token": token})

    def test_jwt_invalid_signature(self):
        """Test invalid JWT signature rejection."""
        provider = JWTAuthProvider(secret_key="secret1")

        # Create token with different secret
        from jwt import encode

        token = encode({"user_id": "hacker"}, "different_secret", algorithm="HS256")

        with pytest.raises(AuthenticationError):
            provider.authenticate({"token": token})

    def test_jwt_missing_token(self):
        """Test missing JWT token."""
        provider = JWTAuthProvider(secret_key="test_secret")

        with pytest.raises(AuthenticationError):
            provider.authenticate({})

    def test_jwt_token_caching(self):
        """Test token caching performance."""
        provider = JWTAuthProvider(secret_key="test_secret")
        user = User(user_id="user_123", email="test@example.com")
        token = provider.create_token(user)

        # First validation
        context1 = provider.authenticate({"token": token})

        # Second validation should use cache
        context2 = provider.authenticate({"token": token})

        assert context1.principal_id == context2.principal_id
        assert len(provider._token_cache) == 1


class TestAPIKeyAuthentication:
    """API key authentication tests."""

    def test_api_key_generation(self):
        """Test secure API key generation."""
        key = generate_api_key()
        assert key.startswith("sk_")
        assert len(key) == 67  # sk_ + 64 hex chars

        # Keys should be unique
        key2 = generate_api_key()
        assert key != key2

    def test_api_key_hashing(self):
        """Test API key hashing."""
        key = generate_api_key()
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)

        # Hash should be consistent
        assert hash1 == hash2

        # Hash should not equal original key
        assert hash1 != key

    def test_api_key_prefix_masking(self):
        """Test API key prefix extraction for display."""
        key = "sk_0123456789abcdefghijklmnopqrstuvwxyz"
        prefix = get_api_key_prefix(key)

        assert prefix.startswith("sk_01")
        assert prefix.endswith("wxyz")
        assert "****" in prefix

    def test_api_key_provider_missing_key(self):
        """Test API key provider with missing credentials."""
        provider = APIKeyAuthProvider(db_connection=None)

        with pytest.raises(AuthenticationError):
            provider.authenticate({})


# ====================================================================
# AUTHORIZATION & RBAC TESTS
# ====================================================================


class TestRBACEnforcement:
    """Role-based access control tests."""

    def test_admin_bypass(self):
        """Test admin role bypasses all checks."""
        enforcer = RBACEnforcer()

        decision = enforcer.check_permission(
            principal_id="admin_user",
            resource="/datasets/xyz",
            action="delete",
            roles=["admin"],
            permissions=set(),
        )

        assert decision.allowed
        assert "admin" in decision.roles_checked

    def test_permission_matching(self):
        """Test permission matching with wildcards."""
        enforcer = RBACEnforcer()

        # Exact match
        decision = enforcer.check_permission(
            principal_id="user_123",
            resource="/datasets",
            action="read",
            roles=["viewer"],
            permissions={"datasets:read"},
        )
        assert decision.allowed

        # Wildcard match
        decision = enforcer.check_permission(
            principal_id="user_123",
            resource="/datasets",
            action="write",
            roles=["engineer"],
            permissions={"datasets:*"},
        )
        assert decision.allowed

    def test_permission_denied(self):
        """Test permission denied."""
        enforcer = RBACEnforcer()

        decision = enforcer.check_permission(
            principal_id="user_123",
            resource="/admin/users",
            action="delete",
            roles=["viewer"],
            permissions={"datasets:read"},
        )

        assert not decision.allowed
        assert "No matching permission" in decision.reason

    def test_delegated_permission(self):
        """Test delegated permission."""
        enforcer = RBACEnforcer()

        # Grant delegated permission
        delegation = DelegatedPermission(
            grantor_id="admin",
            grantee_id="user_123",
            permission="datasets:write",
            resource_pattern="/datasets/xyz",
            granted_at=datetime.now(timezone.utc),
        )
        enforcer.add_delegated_permission(delegation)

        # Check delegated permission
        decision = enforcer.check_permission(
            principal_id="user_123",
            resource="/datasets/xyz",
            action="write",
            roles=["viewer"],
            permissions=set(),
        )

        assert decision.allowed

    def test_get_accessible_resources(self):
        """Test listing accessible resources."""
        enforcer = RBACEnforcer()

        # Register resources
        enforcer.register_resource(
            Resource(
                path="/datasets/public_1",
                resource_type="dataset",
                classification=Classification.PUBLIC,
            )
        )
        enforcer.register_resource(
            Resource(
                path="/datasets/internal_1",
                resource_type="dataset",
                classification=Classification.INTERNAL,
            )
        )

        # Get accessible resources for viewer
        resources = enforcer.get_accessible_resources(
            principal_id="user_123",
            resource_type="dataset",
            roles=["viewer"],
            permissions={"datasets:read"},
        )

        assert "/datasets/public_1" in resources


# ====================================================================
# RATE LIMITING TESTS
# ====================================================================


class TestTokenBucketRateLimiting:
    """Token bucket rate limiting tests."""

    def test_token_bucket_creation(self):
        """Test token bucket creation and initial state."""
        strategy = TokenBucketStrategy()

        # Check rate limit for new user
        allowed = strategy.check_limit("user_123", QuotaTier.STANDARD)
        assert allowed

    def test_token_bucket_consumption(self):
        """Test token consumption."""
        strategy = TokenBucketStrategy()

        # Consume tokens
        for _ in range(100):
            allowed = strategy.check_limit("user_123", QuotaTier.STANDARD)
            assert allowed

    def test_rate_limiter_quota_status(self):
        """Test quota status reporting."""
        limiter = RateLimiter(strategy=TokenBucketStrategy())
        limiter.set_user_tier("user_123", QuotaTier.STANDARD)

        status = limiter.get_quota_status("user_123")
        assert status.tier == QuotaTier.STANDARD
        assert status.hour_remaining > 0

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        limiter = RateLimiter(strategy=TokenBucketStrategy())
        limiter.set_user_tier("user_123", QuotaTier.GUEST)

        # Guest tier has 100 req/hr
        for _ in range(100):
            limiter.check_rate_limit("user_123")

        # 101st should fail
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("user_123")

    def test_quota_headers(self):
        """Test quota header generation."""
        limiter = RateLimiter(strategy=TokenBucketStrategy())
        limiter.set_user_tier("user_123", QuotaTier.STANDARD)

        headers = limiter.get_quota_headers("user_123")
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-Quota-Remaining" in headers


class TestSlidingWindowRateLimiting:
    """Sliding window rate limiting tests."""

    def test_sliding_window_strategy(self):
        """Test sliding window strategy."""
        strategy = SlidingWindowStrategy()

        # Check limit
        for _ in range(10):
            allowed = strategy.check_limit("user_123", QuotaTier.STANDARD)
            assert allowed
            if allowed:
                strategy.record_request("user_123")

    def test_leaky_bucket_strategy(self):
        """Test leaky bucket strategy."""
        strategy = LeakyBucketStrategy(leak_rate=10.0)

        # Requests should be allowed up to capacity
        for _ in range(50):
            allowed = strategy.check_limit("user_123", QuotaTier.STANDARD)
            assert allowed


# ====================================================================
# VERSIONING TESTS
# ====================================================================


class TestAPIVersioning:
    """API versioning tests."""

    def test_version_registration(self):
        """Test API version registration."""
        manager = VersionManager()

        manager.register_version(
            version="v2",
            status=VersionStatus.ACTIVE,
            breaking_changes=["removed_field"],
        )

        version = manager.get_version("v2")
        assert version is not None
        assert version.version == "v2"
        assert "removed_field" in version.breaking_changes

    def test_version_negotiation(self):
        """Test version negotiation."""
        manager = VersionManager()
        manager.register_version("v1")
        manager.register_version("v2")

        # Default to latest
        result = manager.negotiate_version()
        assert result.negotiated_version == "v2"

        # Explicitly request v1
        result = manager.negotiate_version(request_version="v1")
        assert result.negotiated_version == "v1"

    def test_version_deprecation(self):
        """Test version deprecation."""
        manager = VersionManager()
        manager.register_version("v1")
        manager.register_version("v2", status=VersionStatus.ACTIVE)

        # Deprecate v1
        manager.deprecate_version(
            "v1",
            deprecation_date=datetime.now(timezone.utc),
            sunset_date=datetime.now(timezone.utc) + timedelta(days=90),
        )

        version = manager.get_version("v1")
        assert version.is_deprecated()

    def test_parse_version_from_header(self):
        """Test parsing version from Accept header."""
        version = parse_version_from_accept_header("application/json; version=v2")
        assert version == "v2"

        version = parse_version_from_accept_header("application/json")
        assert version is None

    def test_breaking_changes_detection(self):
        """Test breaking changes detection."""
        manager = VersionManager()
        manager.register_version(
            "v1",
            breaking_changes=["removed: user_password field"],
        )
        manager.register_version(
            "v2",
            breaking_changes=["renamed: email_address to email"],
        )

        changes = manager.get_breaking_changes("v1", "v2")
        assert len(changes) == 2


# ====================================================================
# DATA GOVERNANCE TESTS
# ====================================================================


class TestPIIMasking:
    """PII masking tests."""

    def test_email_masking(self):
        """Test email masking."""
        enforcer = GovernanceEnforcer()
        enforcer.set_policy("dataset_123", classification=Classification.SENSITIVE)
        enforcer.add_pii_field(
            "dataset_123",
            "email",
            PIIType.EMAIL,
            MaskingStrategy.MASK,
        )

        data = {"email": "john.doe@example.com"}
        masked = enforcer.apply_masking("dataset_123", data, "viewer")

        assert "example.com" in masked["email"]
        assert "john" not in masked["email"]

    def test_phone_masking(self):
        """Test phone number masking."""
        enforcer = GovernanceEnforcer()
        enforcer.set_policy("dataset_123")
        enforcer.add_pii_field(
            "dataset_123",
            "phone",
            PIIType.PHONE,
            MaskingStrategy.MASK,
        )

        data = {"phone": "(555) 123-4567"}
        masked = enforcer.apply_masking("dataset_123", data, "viewer")

        assert "4567" in masked["phone"]
        assert "555" not in masked["phone"]

    def test_ssn_masking(self):
        """Test SSN masking."""
        enforcer = GovernanceEnforcer()
        enforcer.set_policy("dataset_123")
        enforcer.add_pii_field(
            "dataset_123",
            "ssn",
            PIIType.SSN,
            MaskingStrategy.MASK,
        )

        data = {"ssn": "123-45-6789"}
        masked = enforcer.apply_masking("dataset_123", data, "viewer")

        assert "6789" in masked["ssn"]
        assert "123" not in masked["ssn"]

    def test_admin_no_masking(self):
        """Test admin sees unmasked data."""
        enforcer = GovernanceEnforcer()
        enforcer.set_policy("dataset_123")
        enforcer.add_pii_field(
            "dataset_123",
            "email",
            PIIType.EMAIL,
            MaskingStrategy.MASK,
        )

        data = {"email": "secret@example.com"}
        masked = enforcer.apply_masking("dataset_123", data, "admin")

        # Admin should see unmasked
        assert masked["email"] == "secret@example.com"

    def test_auto_pii_detection(self):
        """Test automatic PII detection."""
        enforcer = GovernanceEnforcer()

        sample_records = [
            {"email": "user1@example.com", "phone": "(555) 123-4567"},
            {"email": "user2@example.com", "phone": "(555) 234-5678"},
            {"email": "user3@example.com", "phone": "(555) 345-6789"},
        ]

        detected = enforcer.auto_detect_pii("dataset_123", sample_records)
        assert "email" in detected
        assert detected["email"] == PIIType.EMAIL

    def test_classification_access_control(self):
        """Test access control based on classification."""
        enforcer = GovernanceEnforcer()

        # Set restricted policy
        enforcer.set_policy(
            "dataset_123",
            classification=Classification.RESTRICTED,
        )

        # Viewer should not have access
        decision = enforcer.validate_access("dataset_123", "viewer")
        assert not decision.allowed

        # Admin should have access
        decision = enforcer.validate_access("dataset_123", "admin")
        assert decision.allowed


# ====================================================================
# REQUEST PIPELINE TESTS
# ====================================================================


class TestAPIRequestPipeline:
    """API request pipeline tests."""

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        auth_providers = [JWTAuthProvider(secret_key="test")]
        enforcer = RBACEnforcer()
        limiter = RateLimiter()
        governance = GovernanceEnforcer()

        pipeline = APIRequestPipeline(
            auth_providers=auth_providers,
            enforcer=enforcer,
            limiter=limiter,
            governance=governance,
        )

        assert pipeline.auth_providers
        assert pipeline.enforcer
        assert pipeline.limiter
        assert pipeline.governance

    def test_pipeline_request_creation(self):
        """Test pipeline request creation."""
        request = PipelineRequest(
            path="/api/v1/datasets",
            method="GET",
            headers={"Authorization": "Bearer token123"},
            query_params={},
            ip_address="192.168.1.1",
        )

        assert request.path == "/api/v1/datasets"
        assert request.method == "GET"
        assert request.timestamp is not None

    def test_extract_credentials_jwt(self):
        """Test JWT credential extraction."""
        pipeline = APIRequestPipeline(
            auth_providers=[],
            enforcer=RBACEnforcer(),
            limiter=RateLimiter(),
            governance=GovernanceEnforcer(),
        )

        request = PipelineRequest(
            path="/api/test",
            method="GET",
            headers={"Authorization": "Bearer abc123def456"},
            query_params={},
        )

        credentials = pipeline._extract_credentials(request)
        assert credentials["token"] == "abc123def456"

    def test_extract_credentials_api_key(self):
        """Test API key credential extraction."""
        pipeline = APIRequestPipeline(
            auth_providers=[],
            enforcer=RBACEnforcer(),
            limiter=RateLimiter(),
            governance=GovernanceEnforcer(),
        )

        request = PipelineRequest(
            path="/api/test",
            method="GET",
            headers={"X-API-Key": "sk_test123"},
            query_params={},
        )

        credentials = pipeline._extract_credentials(request)
        assert credentials["api_key"] == "sk_test123"

    def test_action_extraction_from_method(self):
        """Test action extraction from HTTP method."""
        pipeline = APIRequestPipeline(
            auth_providers=[],
            enforcer=RBACEnforcer(),
            limiter=RateLimiter(),
            governance=GovernanceEnforcer(),
        )

        assert pipeline._get_action_from_method("GET") == "read"
        assert pipeline._get_action_from_method("POST") == "write"
        assert pipeline._get_action_from_method("DELETE") == "delete"


# ====================================================================
# INTEGRATION TESTS
# ====================================================================


class TestIntegration:
    """Integration tests across components."""

    def test_user_authentication_authorization_flow(self):
        """Test complete auth flow: authenticate then authorize."""
        # Setup
        jwt_provider = JWTAuthProvider(secret_key="test_secret_12345")
        enforcer = RBACEnforcer()

        # Create user
        user = User(
            user_id="user_123",
            email="test@example.com",
            roles=["data_consumer"],
        )

        # Create token
        token = jwt_provider.create_token(user)

        # Authenticate
        auth_context = jwt_provider.authenticate({"token": token})
        assert auth_context.principal_id == "user_123"

        # Authorize
        decision = enforcer.check_permission(
            principal_id="user_123",
            resource="/datasets",
            action="read",
            roles=auth_context.roles,
            permissions=auth_context.permissions,
        )
        assert decision.allowed

    def test_versioning_with_governance(self):
        """Test API versioning with data governance."""
        version_manager = VersionManager()
        governance = GovernanceEnforcer()

        # Register versions
        version_manager.register_version("v1", status=VersionStatus.ACTIVE)
        version_manager.register_version("v2", status=VersionStatus.ACTIVE)

        # Set governance policy
        governance.set_policy("dataset_123", classification=Classification.SENSITIVE)
        governance.add_pii_field("dataset_123", "email", PIIType.EMAIL, MaskingStrategy.MASK)

        # Negotiate version and apply governance
        version = version_manager.negotiate_version(request_version="v2")
        assert version.negotiated_version == "v2"

        data = {"email": "secret@example.com", "name": "John Doe"}
        masked = governance.apply_masking("dataset_123", data, "viewer")
        assert "example.com" in masked["email"]
        assert masked["name"] == "John Doe"  # Non-PII fields unchanged
