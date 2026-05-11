# GitHub Actions Secrets Configuration Guide

Complete guide for configuring GitHub repository secrets for CI/CD automation with the NYC Sidewalk Toolkit.

## Overview

GitHub Secrets are encrypted environment variables that GitHub Actions uses for:
- Docker registry authentication (ECR)
- AWS credentials
- API keys (OpenAI, Socrata)
- Database credentials
- TLS certificates

## Prerequisites

- GitHub repository admin access
- AWS IAM credentials
- ECR repository created
- API keys generated

## Step 1: Create AWS IAM User for GitHub Actions

```bash
# Create IAM user
aws iam create-user --user-name github-actions-ci

# Create access key
aws iam create-access-key --user-name github-actions-ci

# Save the Access Key ID and Secret Access Key (shown only once!)
# Store in secure location
```

## Step 2: Attach IAM Policies

```bash
# Create policy document
cat > ecr-github-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:us-east-1:123456789012:repository/nyc-sidewalk-*"
    }
  ]
}
EOF

# Create policy
aws iam create-policy \
  --policy-name github-actions-ecr \
  --policy-document file://ecr-github-policy.json

# Attach to user
aws iam attach-user-policy \
  --user-name github-actions-ci \
  --policy-arn arn:aws:iam::123456789012:policy/github-actions-ecr
```

## Step 3: Add Secrets to GitHub

Navigate to: `Settings → Secrets and variables → Actions → New repository secret`

### AWS Credentials

**Secret Name:** `AWS_ACCESS_KEY_ID`
**Value:** `AKIA...` (from IAM user creation)

**Secret Name:** `AWS_SECRET_ACCESS_KEY`
**Value:** `wJalrXUtn...` (from IAM user creation)

**Secret Name:** `AWS_REGION`
**Value:** `us-east-1`

**Secret Name:** `AWS_ACCOUNT_ID`
**Value:** `123456789012`

### Docker Registry

**Secret Name:** `ECR_REGISTRY`
**Value:** `123456789012.dkr.ecr.us-east-1.amazonaws.com`

**Secret Name:** `ECR_REPOSITORY_API`
**Value:** `nyc-sidewalk-api`

**Secret Name:** `ECR_REPOSITORY_WEB`
**Value:** `nyc-sidewalk-web`

### API Keys

**Secret Name:** `OPENAI_API_KEY`
**Value:** `sk-...` (your OpenAI API key)

**Secret Name:** `SOCRATA_APP_TOKEN`
**Value:** `your-socrata-token`

**Secret Name:** `HUGGINGFACE_API_TOKEN`
**Value:** `hf_...` (your Hugging Face token)

### Database & Infrastructure

**Secret Name:** `DB_PASSWORD`
**Value:** `your-secure-db-password` (minimum 16 characters, complex)

**Secret Name:** `DOCKER_BUILDKIT`
**Value:** `1`

**Secret Name:** `BUILDKIT_PROGRESS`
**Value:** `plain`

### Docker Hub (Optional - for fallback registry)

**Secret Name:** `DOCKERHUB_USERNAME`
**Value:** `your-dockerhub-username`

**Secret Name:** `DOCKERHUB_PASSWORD`
**Value:** `your-dockerhub-token`

## Step 4: Verify Secrets Configuration

Check GitHub Actions logs (no secrets will be printed):

```bash
# Trigger a workflow
git push origin main

# Navigate to Actions tab in GitHub
# Click on the latest workflow run
# Verify "Log OIDC Token" step completes successfully
```

## Step 5: Configure OIDC (Recommended for Enhanced Security)

Using OIDC eliminates need for long-lived AWS credentials:

```bash
# Create OIDC provider (one-time)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create IAM role for GitHub Actions
aws iam create-role \
  --role-name github-actions-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/nyc_data:*"
        }
      }
    }]
  }'

# Attach ECR policy to role
aws iam attach-role-policy \
  --role-name github-actions-role \
  --policy-arn arn:aws:iam::123456789012:policy/github-actions-ecr
```

Then update `.github/workflows/deploy.yml`:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
          aws-region: us-east-1
      
      # Rest of workflow...
```

## Step 6: Update Workflow Files

Update `.github/workflows/deploy.yml` to use secrets:

```yaml
env:
  AWS_REGION: ${{ secrets.AWS_REGION }}
  AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
  ECR_REGISTRY: ${{ secrets.ECR_REGISTRY }}

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password --region ${{ secrets.AWS_REGION }} | \
            docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}
      
      - name: Build API image
        run: |
          docker build \
            -t ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_API }}:latest \
            -t ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_API }}:${{ github.sha }} \
            -f Dockerfile.api .
      
      - name: Push API image
        run: |
          docker push ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_API }}:latest
          docker push ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_API }}:${{ github.sha }}
      
      - name: Build Web image
        run: |
          docker build \
            -t ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_WEB }}:latest \
            -t ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_WEB }}:${{ github.sha }} \
            --build-arg VITE_API_URL=https://api.nyc-sidewalk.example.com/api/v1 \
            .
      
      - name: Push Web image
        run: |
          docker push ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_WEB }}:latest
          docker push ${{ secrets.ECR_REGISTRY }}/${{ secrets.ECR_REPOSITORY_WEB }}:${{ github.sha }}
```

## Step 7: Configure Repository Secrets as Repository Defaults

Create `secrets.yml` for team reference (not committed):

```yaml
# INTERNAL USE ONLY - DO NOT COMMIT
secrets:
  aws:
    access_key_id: AKIA...
    secret_access_key: wJalrXUtn...
    account_id: "123456789012"
    region: us-east-1
  
  ecr:
    registry: 123456789012.dkr.ecr.us-east-1.amazonaws.com
    repo_api: nyc-sidewalk-api
    repo_web: nyc-sidewalk-web
  
  api_keys:
    openai: sk-...
    socrata: ...
    huggingface: hf_...
  
  database:
    password: <SECURE_PASSWORD>
    host: nyc-sidewalk-db.xxx.us-east-1.rds.amazonaws.com
    user: dot_user
```

## Step 8: Rotate Secrets Periodically

```bash
# Rotate AWS credentials every 90 days
aws iam create-access-key --user-name github-actions-ci

# Delete old key after updating GitHub
aws iam delete-access-key --user-name github-actions-ci --access-key-id AKIA_OLD

# Rotate API keys
# Log into OpenAI console → API Keys → Delete old key → Create new key

# Rotate database password
aws rds modify-db-instance \
  --db-instance-identifier nyc-sidewalk-db \
  --master-user-password <NEW_PASSWORD> \
  --apply-immediately
```

## Step 9: Audit Secret Access

```bash
# View secret access logs
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=github-actions-ci \
  --max-results 10

# Enable CloudTrail for all IAM actions
aws cloudtrail create-trail \
  --name github-actions-audit \
  --s3-bucket-name my-company-audit-logs
```

## Security Best Practices

✅ **Least Privilege**
- Separate IAM user for GitHub Actions (not root account)
- Minimal IAM policies (ECR only, not full AWS access)
- Rotate credentials every 90 days

✅ **Secret Management**
- Never commit secrets to git
- Use GitHub Secrets, not hardcoded env vars
- Encrypt all secrets in transit and at rest

✅ **Monitoring**
- Enable CloudTrail for secret access
- Set up alerts for failed auth attempts
- Review GitHub Actions logs regularly

✅ **Access Control**
- Limit secret access to specific workflows
- Use OIDC instead of long-lived keys when possible
- Require approval for production deployments

## Troubleshooting

### Workflow fails with authentication error

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM permissions
aws iam get-user-policy --user-name github-actions-ci --policy-name github-actions-ecr

# Check ECR repository access
aws ecr describe-repositories --repository-names nyc-sidewalk-api
```

### Docker image push fails

```bash
# Check ECR login
aws ecr get-authorization-token --output text

# Verify repository exists
aws ecr describe-repositories --region us-east-1
```

### Secret values are blank in workflow

```bash
# Verify secret exists in GitHub
curl -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_ORG/nyc_data/actions/secrets

# Check secret name matches exactly (case-sensitive)
# Verify no extra spaces in secret name or value
```

## References

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [OIDC Configuration](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [GitHub Actions Security](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
