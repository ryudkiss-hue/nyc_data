# NYC DOT Toolkit - Production Readiness Guide

Complete checklist and considerations for production deployment, including security, packaging, and enterprise requirements.

**Primary UI:** Dash Mission Control (FastAPI, port 8011)  
**Alternative UI:** Streamlit (secondary, port 8501)  
**Deployment Guide:** See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) for cloud deployment options

## Quick Reference

| Aspect | Current Status | Recommended Action |
|--------|---|---|
| **Authentication** | Environment variables (.env) | Implement vault or add FastAPI auth (OAuth2, JWT) |
| **Python Packaging** | Poetry configured | Test `poetry build` before release |
| **Encryption** | PostgreSQL capable | Enable pgcrypto extension |
| **Audit Trails** | CDC event logging | Configure retention policies |
| **Backups** | Manual scripts provided | Automate daily backups |
| **Monitoring** | Prometheus + Grafana included | Configure dashboards |
| **API Keys** | Environment-based | Implement key rotation |
| **Licensing** | MIT | Include in distributions |

---

## Authentication Implementation (Simple to Advanced)

### Current State: Environment Variables

Works for development but NOT secure for production:

```bash
# .env.socrata (insecure for production)
POSTGRES_PASSWORD=mypassword123
SOCRATA_APP_TOKEN=abc123def456
```

**Risks**:
- ❌ Passwords visible in files
- ❌ Easy to commit to git
- ❌ No audit trail of access
- ❌ No expiration/rotation

### Immediate: Add .gitignore Protection

```bash
# .gitignore
.env.socrata
.env.*.local
secrets/
*.key
*.pem
```

Add pre-commit hook to prevent secret commits:

```bash
# .pre-commit-config.yaml (add this)
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: detect-private-key
```

### Quick Implementation: Streamlit Authentication

Add password protection to dashboard in 5 minutes:

```python
# socrata_toolkit/app.py (add to top)
import streamlit as st

# Simple password protection
def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        with st.form("my_form"):
            st.write("Enter password to access NYC DOT Dashboard")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Submit")
            if submitted:
                if password == st.secrets["app_password"]:
                    st.session_state.password_correct = True
                    st.rerun()
                else:
                    st.error("😕 Password incorrect")
        return False
    return True

# At the start of app.py
if not check_password():
    st.stop()

# Rest of dashboard code...
st.title("NYC DOT Sidewalk Toolkit")
```

Add password to `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml (add to .gitignore)
app_password = "secure_password_here"
```

### Medium Implementation: API Key System

For programmatic access:

```python
# socrata_toolkit/api_keys.py
from datetime import datetime, timedelta
import secrets
from sqlalchemy import Column, String, DateTime, Boolean

class APIKey(Base):
    """API key for external access."""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True)
    key = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime)
    
    @classmethod
    def create(cls, name: str, days: int = 90) -> 'APIKey':
        return cls(
            id=secrets.token_hex(16),
            key=f"sk_{secrets.token_urlsafe(32)}",
            name=name,
            expires_at=datetime.utcnow() + timedelta(days=days)
        )
```

Create CLI command for key management:

```bash
# socrata_toolkit/cli.py (add command)
@main.command("api-key-create")
@click.option("--name", required=True, help="Key name")
@click.option("--days", type=int, default=90, help="Expiration days")
def create_api_key(name: str, days: int):
    """Create new API key."""
    from socrata_toolkit.api_keys import APIKey
    key = APIKey.create(name, days)
    db.add(key)
    db.commit()
    click.echo(f"API Key created: {key.key}")
    click.echo(f"Expires: {key.expires_at.isoformat()}")

# Usage
socrata api-key-create --name "external_service" --days 365
```

### Advanced Implementation: External Vault (Recommended for Production)

Use **HashiCorp Vault** (enterprise-grade secret management):

```bash
# 1. Install Vault (5 minutes)
# https://www.vaultproject.io/downloads

# 2. Start Vault server
vault server -dev

# 3. Unseal Vault and set environment variables
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='s.xxxxxxxxxxxxxxxx'

# 4. Add secrets
vault kv put secret/nycdot/postgres \
  username="dot_user" \
  password="strong_password"

vault kv put secret/nycdot/socrata \
  api_token="your_token_here"

# 5. Python code
import hvac

def get_postgres_password():
    client = hvac.Client(url='http://127.0.0.1:8200', token=os.getenv('VAULT_TOKEN'))
    secret = client.secrets.kv.v2.read_secret_version(path='nycdot/postgres')
    return secret['data']['data']['password']
```

---

## Python Package Wrapping

### Current State: Poetry + pip

Already configured. Just need to test and publish.

### Step 1: Test Package Build Locally

```bash
# Install build tools
pip install build twine

# Build wheel and source distribution
python -m build

# Should create:
# dist/socrata_toolkit-0.3.0-py3-none-any.whl
# dist/socrata_toolkit-0.3.0.tar.gz

# Verify wheel contents
unzip -l dist/socrata_toolkit-0.3.0-py3-none-any.whl | head -20

# Install from local wheel
pip install dist/socrata_toolkit-0.3.0-py3-none-any.whl

# Test import
python -c "import socrata_toolkit; print(socrata_toolkit.__version__)"
```

### Step 2: Publish Options

**Option A: Public PyPI (Open Source)**

```bash
# 1. Create account at https://pypi.org/account/register/

# 2. Generate API token from account settings

# 3. Configure credentials
cat > ~/.pypirc << EOF
[distutils]
index-servers =
    pypi

[pypi]
username = __token__
password = pypi_AgENdGV5... # your token
EOF

# 4. Build and publish
python -m build
twine upload dist/*

# Users install with:
pip install socrata_toolkit

# Or specific version:
pip install socrata_toolkit==0.3.0
```

**Option B: Private PyPI (Corporate)**

```bash
# Using AWS CodeArtifact (AWS-hosted)
aws codeartifact login --tool pip --domain nycdot --domain-owner 123456789012

# Build and upload
python -m build
twine upload dist/ --repository codeartifact

# Users configure credentials:
pip config set global.index-url https://pypi-nycdot-xxxxx.d.codeartifact.us-east-1.amazonaws.com/simple/
pip install socrata_toolkit
```

**Option C: GitHub Packages**

```bash
# 1. Generate GitHub personal access token
# 2. Create ~/.pypirc
[distutils]
index-servers = github

[github]
repository = https://github.com/nychealth/socrata_toolkit
username = __token__
password = ghp_xxxxxxxxxxxxx

# 3. Publish
twine upload --repository github dist/*

# 4. Users install (requires auth)
pip install -i https://github.com/nychealth/socrata_toolkit
```

**Option D: Local/Corporate Distribution**

```bash
# For internal-only distribution
python -m build

# Copy wheel to corporate repository:
# - SharePoint
# - Internal wiki
# - USB drive
# - File server

# Users install:
pip install socrata_toolkit-0.3.0-py3-none-any.whl
```

### Step 3: Version Management

```bash
# Update version in pyproject.toml
# Before building, bump version:
[tool.poetry]
version = "0.4.0"  # Changed from 0.3.0

# Document changes in CHANGELOG.md
# Then build and publish
poetry build
poetry publish
```

---

## Other Critical Considerations

### 1. Audit & Compliance Requirements

The toolkit already logs all changes via CDC. Configure retention:

```bash
# .env.socrata
AUDIT_RETENTION_DAYS=730  # 2 years
AUDIT_LOG_LEVEL=INFO
```

Query audit history:

```bash
# View all changes to a table
docker-compose exec postgres psql -U dot_user -d sidewalk_db << EOF
SELECT 
    timestamp,
    operation,
    before_value,
    after_value,
    user
FROM cdc_audit_log
WHERE table_name = 'sidewalk_inspections'
ORDER BY timestamp DESC
LIMIT 100;
EOF
```

### 2. Performance Optimization

Monitor query performance:

```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log slow queries (>1s)
SELECT pg_reload_conf();

-- Check slow query log
docker-compose exec postgres tail -f /var/log/postgresql/postgresql.log
```

Add indexes for common queries:

```sql
-- Create indexes for common filters
CREATE INDEX idx_inspections_borough ON sidewalk_inspections(borough);
CREATE INDEX idx_inspections_date ON sidewalk_inspections(inspection_date);
CREATE INDEX idx_contracts_status ON contracts(status);
```

### 3. High Availability Setup

For production with uptime requirements:

```yaml
# docker-compose-ha.yml
version: '3.9'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_REPLICATION_MODE: master
    volumes:
      - pgdata1:/var/lib/postgresql/data
  
  postgres-replica:
    image: postgres:16
    environment:
      POSTGRES_REPLICATION_MODE: slave
    depends_on:
      - postgres
    volumes:
      - pgdata2:/var/lib/postgresql/data
  
  pgbouncer:
    image: edoburu/pgbouncer
    environment:
      DATABASE_URL: "postgres://dot_user:password@postgres:5432/sidewalk_db"
    ports:
      - "6432:6432"
```

### 4. Data Migration Safety

When upgrading database schema:

```bash
# 1. Create backup
docker-compose exec postgres pg_dump -U dot_user sidewalk_db > backup.sql

# 2. Test migration on copy
docker run -e PGPASSWORD=password postgres:16 psql \
  -h postgres -U dot_user -d sidewalk_db \
  -f migration.sql --dry-run

# 3. Apply migration
docker-compose exec postgres psql -U dot_user -d sidewalk_db -f migration.sql

# 4. Verify data integrity
docker-compose exec postgres psql -U dot_user -d sidewalk_db << EOF
SELECT COUNT(*) as record_count FROM sidewalk_inspections;
SELECT COUNT(*) as contract_count FROM contracts;
EOF
```

### 5. Dependency Management

Keep dependencies up to date:

```bash
# Check for outdated packages
pip list --outdated

# Check for security vulnerabilities
pip install safety
safety check

# Or use newer pip-audit
pip install pip-audit
pip-audit

# Update dependencies safely
pip install --upgrade pip
poetry update
```

### 6. Containerization for Distribution

Create standalone Docker image:

```dockerfile
# Dockerfile.production
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY socrata_toolkit /app/socrata_toolkit
COPY pyproject.toml README.md ./

# Install with production settings
RUN pip install --no-cache-dir ".[all]"

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socrata_toolkit; print('ok')" || exit 1

# Default command
CMD ["python", "launcher.py", "web"]
```

Build and distribute:

```bash
# Build production image (Dash Mission Control primary)
docker build -t nycdot/socrata-toolkit:0.5.0 --target mission .

# Test image (Dash at port 8011)
docker run -e SOCRATA_APP_TOKEN=test -p 8011:8011 \
    nycdot/socrata-toolkit:0.5.0

# Push to registry
docker tag nycdot/socrata-toolkit:0.5.0 \
    registry.example.com/nycdot/socrata-toolkit:0.5.0
docker push registry.example.com/nycdot/socrata-toolkit:0.5.0

# Users run with:
docker pull registry.example.com/nycdot/socrata-toolkit:0.5.0
docker run -e SOCRATA_APP_TOKEN=your_token -p 8011:8011 \
    registry.example.com/nycdot/socrata-toolkit:0.5.0
# → http://localhost:8011 (Dash Mission Control)
```

---

## Pre-Production Checklist

### Security
- [ ] All secrets moved to vault or secure storage
- [ ] .env files in .gitignore
- [ ] No hardcoded passwords in code
- [ ] HTTPS/TLS enabled for all connections
- [ ] Database encrypted at rest
- [ ] API rate limiting configured
- [ ] Authentication enabled (Streamlit + API)
- [ ] Audit logging enabled and tested
- [ ] Dependencies scanned for vulnerabilities

### Operations
- [ ] Automated daily backups working
- [ ] Restore from backup tested
- [ ] Monitoring dashboards set up (Grafana)
- [ ] Alerting configured
- [ ] Log aggregation working
- [ ] Performance baselines established
- [ ] Scaling plan documented
- [ ] Runbook created for common tasks
- [ ] On-call rotation established

### Quality
- [ ] All tests passing (100%)
- [ ] Code coverage > 80%
- [ ] Linting passes (zero warnings)
- [ ] Documentation complete
- [ ] API endpoints documented
- [ ] Known limitations documented
- [ ] Release notes prepared

### Deployment
- [ ] Package tested (local wheel install)
- [ ] Version number bumped
- [ ] CHANGELOG.md updated
- [ ] README.md verified
- [ ] Docker image built and tested
- [ ] Deployment script tested
- [ ] Rollback procedure documented
- [ ] Change management approved

### Compliance
- [ ] License compliance verified
- [ ] Data retention policy configured
- [ ] PII handling documented
- [ ] HIPAA/GDPR compliance checked
- [ ] SOC 2 requirements mapped
- [ ] Incident response plan ready

---

## Day-1 Production Tasks

### Hour 1: Verification
```bash
# Verify all services running
docker-compose ps

# Check database connectivity
python launcher.py doctor

# Test CLI commands
socrata search --query test

# Access Dash Mission Control dashboard (PRIMARY)
# http://localhost:8011
# 
# Or Streamlit fallback (if needed)
# http://localhost:8501
```

### Hour 2: Monitoring Setup
```bash
# Configure Grafana dashboards
# http://localhost:3000

# Set up alerts for:
# - PostgreSQL availability
# - Memory usage
# - Disk space
# - API response times
# - Error rates
```

### Hour 3: Backup Verification
```bash
# Test backup process
make db-backup

# Verify backup file
ls -lh backups/

# Test restore from backup
make db-restore  # (if implemented)
```

### Hour 4: Documentation
```bash
# Create runbook for common tasks
# - How to restart services
# - How to view logs
# - How to restore from backup
# - How to add users
# - How to scale

# Post in team wiki/documentation
```

---

## Ongoing Maintenance

### Weekly
- [ ] Review error logs
- [ ] Check backup status
- [ ] Monitor disk usage

### Monthly
- [ ] Update dependencies
- [ ] Review security logs
- [ ] Capacity planning review
- [ ] Test disaster recovery

### Quarterly
- [ ] Security audit
- [ ] Performance tuning
- [ ] Documentation review
- [ ] Team training

---

## Support Resources

- **Security**: [SECURITY_AND_PACKAGING.md](SECURITY_AND_PACKAGING.md)
- **Deployment**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Quick Start**: [QUICKSTART.md](../QUICKSTART.md)
- **Package Info**: [EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md)

---

**Version**: 0.3.0  
**Last Updated**: 2026-05-11  
**Status**: Ready for Production Deployment
