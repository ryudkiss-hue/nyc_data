# NYC DOT Toolkit - Security, Authentication & Packaging Guide

Comprehensive security, authentication, and Python package distribution guidance.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Passwords](#authentication--passwords)
3. [Python Package Distribution](#python-package-distribution)
4. [Other Critical Considerations](#other-critical-considerations)
5. [Production Checklist](#production-checklist)

---

## Security Overview

### Current Architecture

The NYC DOT Toolkit uses a **zero-trust, defense-in-depth** security model:

```
┌────────────────────────────────────────────────────────┐
│                  NYC DOT Toolkit Security              │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: Network & Transport                         │
│  ├─ HTTPS/TLS for all external APIs                   │
│  ├─ PostgreSQL SSL connections (optional)             │
│  ├─ Docker internal networking (isolated)             │
│  └─ Firewall rules (localhost only by default)        │
│                                                         │
│  Layer 2: Authentication & Authorization              │
│  ├─ Environment variable credentials (.env.socrata)  │
│  ├─ PostgreSQL user/password authentication           │
│  ├─ Socrata API token validation                      │
│  ├─ Streamlit session management                      │
│  └─ Role-based access control (RBAC)                  │
│                                                         │
│  Layer 3: Data Protection                             │
│  ├─ CDC audit logging (all changes tracked)           │
│  ├─ Schema validation (prevent bad data)              │
│  ├─ Lineage tracking (data provenance)                │
│  ├─ Compliance checking (design rules enforced)       │
│  └─ Encryption at rest (PostgreSQL pgcrypto)          │
│                                                         │
│  Layer 4: Application Security                        │
│  ├─ Input validation and sanitization                 │
│  ├─ SQL injection prevention (parameterized queries) │
│  ├─ Rate limiting (API throttling)                    │
│  ├─ Logging and monitoring (audit trails)             │
│  └─ Error handling (no sensitive data exposure)       │
│                                                         │
└────────────────────────────────────────────────────────┘
```

---

## Authentication & Passwords

### Current Implementation

#### 1. Environment Variables (`.env.socrata`)

```bash
# Socrata API Token
SOCRATA_APP_TOKEN=your_app_token_here

# PostgreSQL Credentials
POSTGRES_USER=dot_user
POSTGRES_PASSWORD=strong_password_here

# Grafana Admin
GRAFANA_ADMIN_PASSWORD=strong_password_here

# Azure Cognitive Services (optional)
AZURE_COGNITIVE_KEY=your_key_here
```

**⚠️ Security Note**: Environment variables are flexible but store secrets in plaintext.

### Recommended Security Enhancements

#### Option 1: Vault Integration (Production-Grade)

Use **HashiCorp Vault** or **AWS Secrets Manager**:

```python
# socrata_toolkit/security.py
import hvac
from pathlib import Path

class VaultSecretManager:
    """Manages secrets using HashiCorp Vault."""
    
    def __init__(self, vault_addr: str, vault_token: str):
        self.client = hvac.Client(url=vault_addr, token=vault_token)
    
    def get_secret(self, path: str, key: str) -> str:
        """Retrieve secret from Vault."""
        secret = self.client.secrets.kv.v2.read_secret_version(path)
        return secret['data']['data'][key]
    
    def get_postgres_dsn(self) -> str:
        """Get PostgreSQL DSN from Vault."""
        user = self.get_secret("database/postgres", "username")
        password = self.get_secret("database/postgres", "password")
        host = self.get_secret("database/postgres", "host")
        return f"postgresql://{user}:{password}@{host}:5432/sidewalk_db"

# Usage
vault = VaultSecretManager(
    vault_addr="https://vault.example.com:8200",
    vault_token=os.getenv("VAULT_TOKEN")
)
dsn = vault.get_postgres_dsn()
```

Install Vault support:
```bash
pip install hvac
```

#### Option 2: AWS Secrets Manager (AWS-Hosted)

```python
# socrata_toolkit/security.py
import boto3
import json

class AWSSecretManager:
    """Manages secrets using AWS Secrets Manager."""
    
    def __init__(self, region: str = "us-east-1"):
        self.client = boto3.client("secretsmanager", region_name=region)
    
    def get_secret(self, secret_name: str) -> dict:
        """Retrieve secret from AWS."""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            raise ValueError(f"Failed to retrieve secret {secret_name}: {e}")

# Usage
secrets = AWSSecretManager()
db_creds = secrets.get_secret("nyc_dot/postgres")
socrata_token = secrets.get_secret("nyc_dot/socrata_api_token")
```

Install AWS support:
```bash
pip install boto3
```

#### Option 3: Azure Key Vault (Microsoft Ecosystem)

```python
# socrata_toolkit/security.py
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class AzureKeyVaultManager:
    """Manages secrets using Azure Key Vault."""
    
    def __init__(self, vault_url: str):
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=credential)
    
    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Azure Key Vault."""
        return self.client.get_secret(secret_name).value

# Usage
vault = AzureKeyVaultManager(
    vault_url="https://nycdot-keyvault.vault.azure.us"
)
postgres_password = vault.get_secret("postgres-password")
```

Install Azure support:
```bash
pip install azure-identity azure-keyvault-secrets
```

#### Option 4: OS Keyring (Local Development)

```python
# socrata_toolkit/security.py
import keyring

class KeyringSecretManager:
    """Manages secrets using OS keyring (development only)."""
    
    @staticmethod
    def get_secret(service: str, key: str) -> str:
        """Retrieve secret from OS keyring."""
        return keyring.get_password(service, key)
    
    @staticmethod
    def set_secret(service: str, key: str, value: str) -> None:
        """Store secret in OS keyring."""
        keyring.set_password(service, key, value)

# Usage
password = KeyringSecretManager.get_secret("nyc_dot", "postgres_password")
```

Install keyring support:
```bash
pip install keyring
```

### Implementation Strategy

Update `launcher.py` to support multiple secret backends:

```python
# launcher.py
def get_secret_manager(backend: str = "env"):
    """Get secret manager based on backend."""
    if backend == "vault":
        from socrata_toolkit.security import VaultSecretManager
        return VaultSecretManager(
            vault_addr=os.getenv("VAULT_ADDR"),
            vault_token=os.getenv("VAULT_TOKEN")
        )
    elif backend == "aws":
        from socrata_toolkit.security import AWSSecretManager
        return AWSSecretManager()
    elif backend == "azure":
        from socrata_toolkit.security import AzureKeyVaultManager
        return AzureKeyVaultManager(
            vault_url=os.getenv("AZURE_VAULT_URL")
        )
    elif backend == "keyring":
        from socrata_toolkit.security import KeyringSecretManager
        return KeyringSecretManager
    else:  # env (default)
        return None  # Use environment variables

# Usage
secrets = get_secret_manager(backend=os.getenv("SECRET_BACKEND", "env"))
```

### Streamlit Authentication

Add optional authentication to Streamlit dashboard:

```python
# socrata_toolkit/app.py
import streamlit as st
from streamlit_authenticator import Authenticate
import yaml

# Load authentication config
with open("auth_config.yaml") as f:
    config = yaml.safe_load(f)

authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
)

# Add authentication
name, authentication_status, username = authenticator.login('main')

if authentication_status:
    authenticator.logout('Logout', 'main')
    st.write(f'Welcome *{name}*')
    # Show dashboard
else:
    st.error('Username/password is incorrect')
```

Install Streamlit auth:
```bash
pip install streamlit-authenticator
```

Create `auth_config.yaml`:
```yaml
credentials:
  usernames:
    dot_analyst:
      email: analyst@nycdot.gov
      name: Analyst User
      password: $2b$12$...  # Hashed password
    dot_manager:
      email: manager@nycdot.gov
      name: Manager User
      password: $2b$12$...  # Hashed password

cookie:
  name: nyc_dot_auth
  key: your_secret_key
  expiry_days: 30

pre-authorized:
  emails:
    - admin@nycdot.gov
```

### API Key Management

For programmatic access:

```python
# socrata_toolkit/api_keys.py
import secrets
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Boolean

class APIKey(Base):
    """API key for programmatic access."""
    __tablename__ = "api_keys"
    
    id = Column(String(32), primary_key=True)
    token = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    description = Column(String(255))
    
    @classmethod
    def create(cls, description: str, expires_days: int = 90) -> 'APIKey':
        """Create new API key."""
        return cls(
            id=secrets.token_hex(16),
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            description=description
        )
    
    def is_valid(self) -> bool:
        """Check if key is still valid."""
        return self.is_active and self.expires_at > datetime.utcnow()

# Usage in API
from fastapi import APIKey, HTTPException

async def verify_api_key(api_key: str) -> APIKey:
    """Verify API key."""
    key = db.query(APIKey).filter(APIKey.token == api_key).first()
    if not key or not key.is_valid():
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key
```

---

## Python Package Distribution

### Current Setup

The toolkit is configured for distribution via Poetry and pip:

```bash
# pyproject.toml (already configured)
[tool.poetry]
name = "socrata_toolkit"
version = "0.3.0"
description = "NYC DOT Sidewalk Inspection & Management Toolkit"

[tool.poetry.scripts]
socrata = "socrata_toolkit.cli:main"
```

### Building the Package

#### Method 1: Poetry (Recommended)

```bash
# Install build dependencies
pip install poetry

# Build wheel and source distribution
poetry build

# Outputs:
# dist/socrata_toolkit-0.3.0-py3-none-any.whl
# dist/socrata_toolkit-0.3.0.tar.gz

# Publish to PyPI (if open-source)
poetry publish
```

#### Method 2: Build Module

```bash
pip install build

# Build wheel and sdist
python -m build

# Same outputs as poetry
```

#### Method 3: Setup.py (Backward Compatible)

Create `setup.py` for compatibility:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="socrata_toolkit",
    version="0.3.0",
    description="NYC DOT Sidewalk Inspection & Management Toolkit",
    author="NYC DOT Development Team",
    author_email="dev@nycdot.gov",
    url="https://github.com/nychealth/socrata_toolkit",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28",
        "pandas>=2.0",
        "pyyaml>=6.0",
        "click>=8.0",
        "numpy>=1.24",
    ],
    extras_require={
        "postgres": ["psycopg-binary>=2.9"],
        "mongo": ["pymongo>=4.0"],
        "xlsx": ["openpyxl>=3.0"],
        "nlp": ["spacy>=3.5"],
        "geo": ["shapely>=2.0"],
        "viz": ["matplotlib>=3.5"],
        "ui": ["streamlit>=1.10"],
        "all": [
            "psycopg-binary>=2.9",
            "pymongo>=4.0",
            "openpyxl>=3.0",
            "spacy>=3.5",
            "shapely>=2.0",
            "matplotlib>=3.5",
            "streamlit>=1.10",
        ],
    },
    entry_points={
        "console_scripts": [
            "socrata=socrata_toolkit.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Shells",
    ],
)
```

### Installation Options

#### For End Users

```bash
# Standard installation (core only)
pip install socrata_toolkit

# With optional features
pip install socrata_toolkit[postgres,xlsx,nlp]

# Everything
pip install socrata_toolkit[all]

# Development version (from GitHub)
pip install git+https://github.com/nychealth/socrata_toolkit.git
```

#### For Development

```bash
# Clone and install in editable mode
git clone https://github.com/nychealth/socrata_toolkit.git
cd socrata_toolkit
pip install -e ".[all,dev]"
```

### Publishing Options

#### Option 1: PyPI (Public)

For open-source distribution:

```bash
# Create PyPI account at https://pypi.org

# Install twine
pip install twine

# Build package
poetry build

# Upload to PyPI
twine upload dist/*

# Then users install with:
pip install socrata_toolkit
```

#### Option 2: Private PyPI (Organization-Only)

For internal use:

```bash
# Using Artifactory, Nexus, or AWS CodeArtifact

# Configure credentials
pip config set global.index-url https://artifactory.nycdot.gov/api/pypi/python/simple

# Publish
twine upload --repository-url https://artifactory.nycdot.gov/api/pypi/pypi dist/*

# Users install same way
pip install socrata_toolkit
```

#### Option 3: GitHub Packages

Use GitHub's package registry:

```bash
# Configure ~/.pypirc
[distutils]
index-servers =
    github

[github]
repository = https://github.com/nychealth/socrata_toolkit
username = __token__
password = ghp_xxxxxxxxxxxx

# Publish
twine upload --repository github dist/*
```

#### Option 4: Local/Corporate Distribution

Package for corporate environment:

```bash
# Create wheel file
python -m build

# Distribute via:
# - USB drive
# - Internal file server
# - SharePoint
# - Email

# Users install from file
pip install socrata_toolkit-0.3.0-py3-none-any.whl
```

---

## Other Critical Considerations

### 1. Audit Logging & Compliance

The toolkit includes comprehensive audit trails:

```python
# socrata_toolkit/governance_processor.py
class GovernanceProcessor:
    def _log_to_audit(self, event: GovernanceEvent) -> None:
        """Log governance event to audit table."""
        audit_record = {
            "timestamp": event.timestamp,
            "operation": event.operation,
            "table": event.table,
            "user": event.user,
            "details": event.details,
            "status": "success" if event.valid else "failed"
        }
        # Logs automatically to CDC event log
```

Configure audit logging in `.env.socrata`:

```bash
# Audit Configuration
AUDIT_LOG_LEVEL=INFO
AUDIT_RETENTION_DAYS=365
AUDIT_ENCRYPTION=true
```

### 2. Rate Limiting & API Throttling

```python
# socrata_toolkit/api.py
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.util import get_remote_address

await FastAPILimiter.init(redis)

@app.get("/api/datasets")
@limiter.limit("100/minute")
async def list_datasets(request: Request):
    """List datasets with rate limiting."""
    return {"datasets": [...]}
```

### 3. Data Encryption at Rest

Enable PostgreSQL encryption:

```sql
-- Create encrypted columns
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE sidewalk_inspections 
ADD COLUMN notes_encrypted text;

-- Encrypt sensitive data
UPDATE sidewalk_inspections 
SET notes_encrypted = pgp_sym_encrypt(notes, 'encryption_key')
WHERE notes IS NOT NULL;
```

### 4. Backup & Disaster Recovery

```bash
# Automated daily backups
# Add to crontab (Linux) or Task Scheduler (Windows)

# Daily backup
0 2 * * * docker-compose -f /app/docker-compose.yml exec postgres \
    pg_dump -U dot_user sidewalk_db | \
    gzip > /backups/sidewalk_$(date +\%Y\%m\%d).sql.gz

# Weekly offsite backup
0 3 * * 0 aws s3 cp /backups/sidewalk_*.sql.gz \
    s3://nycdot-backups/postgres/
```

### 5. Dependency Scanning

Regular vulnerability scanning:

```bash
# Install safety
pip install safety

# Scan dependencies
safety check

# Or use pip-audit (pip native)
pip install pip-audit
pip-audit

# Integration with CI/CD
# (Runs automatically in GitHub Actions)
```

### 6. License Compliance

Toolkit is MIT licensed. Verify dependencies:

```bash
# Check licenses
pip install pip-licenses
pip-licenses

# Generate license report
pip-licenses --format=csv --output-file=licenses.csv
```

### 7. Version Management & Updates

```bash
# Check for updates
pip install --upgrade socrata_toolkit

# Pin specific version
pip install socrata_toolkit==0.3.0

# Stay on minor version
pip install 'socrata_toolkit>=0.3,<0.4'
```

### 8. Error Handling & Logging

```python
# socrata_toolkit/logging_utils.py
import logging

logger = logging.getLogger("socrata_toolkit")

try:
    result = process_data()
except ValueError as e:
    logger.error(f"Validation error: {e}", exc_info=True)
    # Don't expose sensitive details to users
    raise HTTPException(status_code=400, detail="Invalid input")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    # Generic error message
    raise HTTPException(status_code=500, detail="Internal error")
```

---

## Production Checklist

Before deploying to production:

### Security
- [ ] All passwords stored in secret vault (not .env)
- [ ] HTTPS/TLS enabled for all external connections
- [ ] API keys rotated regularly
- [ ] Database encrypted at rest
- [ ] Audit logging enabled
- [ ] Rate limiting configured
- [ ] Security headers set (CORS, CSP, etc.)
- [ ] Dependencies scanned for vulnerabilities
- [ ] Access controls enforced

### Operations
- [ ] Automated backups configured (daily, offsite)
- [ ] Disaster recovery plan tested
- [ ] Monitoring and alerting active
- [ ] Log aggregation configured
- [ ] Performance baselines established
- [ ] Capacity planning completed
- [ ] Documentation updated
- [ ] Team trained

### Compliance
- [ ] Data privacy policy defined
- [ ] HIPAA/GDPR compliance verified
- [ ] Audit trails enabled
- [ ] Data retention policies configured
- [ ] PII handling documented
- [ ] License compliance verified
- [ ] SOC 2 readiness assessed

### Deployment
- [ ] Tests passing (100% pass rate)
- [ ] Code reviewed and approved
- [ ] Staged deployment completed
- [ ] Production environment verified
- [ ] Rollback plan documented
- [ ] Change management followed

---

## Support & Resources

- **Security Policy**: See SECURITY.md in repo
- **Authentication Guide**: docs/SECURITY_AND_PACKAGING.md
- **Package Distribution**: https://packaging.python.org/
- **PyPI Documentation**: https://pypi.org/help/
- **Vault Setup**: https://www.vaultproject.io/docs

---

**Version**: 0.3.0  
**Last Updated**: 2026-05-11  
**Status**: Production Ready
