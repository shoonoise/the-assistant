# Google Cloud Deployment Guide

## Prerequisites

1. **Google Cloud Account**: Set up a Google Cloud project
2. **gcloud CLI**: Install and authenticate
3. **Terraform** (optional): For infrastructure as code
4. **Docker**: For local testing

## Step-by-Step Deployment

### 1. Set up Google Cloud Project

```bash
# Create a new project (optional)
gcloud projects create your-project-id

# Set the project
gcloud config set project your-project-id

# Enable billing (required for Cloud Run and Cloud SQL)
# Do this through the Google Cloud Console
```

### 2. Configure Temporal

You have two options for Temporal:

**Option A: Temporal Cloud (Recommended)**
- Sign up at [cloud.temporal.io](https://cloud.temporal.io)
- Get your namespace endpoint
- Update `TEMPORAL_HOST` in your environment

**Option B: Self-hosted Temporal on GKE**
- Deploy Temporal using Helm charts on Google Kubernetes Engine
- More complex but gives you full control

### 3. Set up Infrastructure with Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -var="project_id=your-project-id" -var="db_password=secure-password"

# Apply the infrastructure
terraform apply -var="project_id=your-project-id" -var="db_password=secure-password"
```

### 4. Configure Secrets

```bash
# Database encryption key (32 characters)
echo -n "your-32-character-encryption-key" | gcloud secrets create db-encryption-key --data-file=-

# JWT secret
echo -n "your-jwt-secret-key" | gcloud secrets create jwt-secret --data-file=-

# Telegram bot token
echo -n "your-telegram-bot-token" | gcloud secrets create telegram-token --data-file=-

# Google OAuth credentials (upload your credentials file)
gcloud secrets create google-oauth-credentials --data-file=path/to/your/google-credentials.json
```

### 5. Update Environment Configuration

Create a production environment configuration:

```bash
# Update cloudbuild.yaml with your actual values
# Set TEMPORAL_HOST to your Temporal Cloud endpoint
# Update DATABASE_URL to use Cloud SQL connection
```

### 6. Deploy with Cloud Build

```bash
# Submit the build
gcloud builds submit --config cloudbuild.yaml

# Or use the deployment script
./scripts/deploy.sh your-project-id us-central1
```

### 7. Configure Domain and SSL (Optional)

```bash
# Map a custom domain to your Cloud Run service
gcloud run domain-mappings create --service=the-assistant-app --domain=your-domain.com --region=us-central1
```

## Environment Variables for Production

Update your Cloud Run services with these environment variables:

```bash
# Core settings
LOG_LEVEL=INFO
PORT=8000

# Database (use Cloud SQL connection string)
DATABASE_URL=postgresql+asyncpg://the_assistant:password@/the_assistant?host=/cloudsql/project:region:instance

# Temporal (use your Temporal Cloud endpoint)
TEMPORAL_HOST=your-namespace.tmprl.cloud:7233
TEMPORAL_NAMESPACE=your-namespace

# Google OAuth (update redirect URI for production)
GOOGLE_OAUTH_REDIRECT_URI=https://your-domain.com/google/oauth2callback

# Obsidian (if using Cloud Storage)
OBSIDIAN_VAULT_PATH=/vault
```

## Monitoring and Logging

### Set up monitoring:

```bash
# Enable Cloud Monitoring
gcloud services enable monitoring.googleapis.com

# View logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50
```

### Health checks are automatically configured for:
- `/health` endpoint for load balancer health checks
- Container health checks in Dockerfile.production

## Scaling Configuration

Cloud Run automatically scales based on traffic, but you can configure:

```bash
# Update scaling settings
gcloud run services update the-assistant-app \
  --region=us-central1 \
  --min-instances=1 \
  --max-instances=10 \
  --concurrency=80
```

## Security Best Practices

1. **Secrets Management**: All sensitive data stored in Secret Manager
2. **IAM**: Use least-privilege service accounts
3. **Network**: Configure VPC connector if needed
4. **Authentication**: Implement proper OAuth flows
5. **HTTPS**: Cloud Run provides automatic SSL certificates

## Cost Optimization

1. **Cloud Run**: Pay per request, scales to zero
2. **Cloud SQL**: Use appropriate instance size
3. **Secrets**: Minimal cost for secret storage
4. **Monitoring**: Basic monitoring is free

## Troubleshooting

### Common issues:

1. **Database connection**: Ensure Cloud SQL proxy is configured
2. **Secrets access**: Check IAM permissions for Secret Manager
3. **Temporal connection**: Verify network connectivity to Temporal Cloud
4. **OAuth redirect**: Update redirect URIs in Google Cloud Console

### Useful commands:

```bash
# Check service status
gcloud run services describe the-assistant-app --region=us-central1

# View logs
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=the-assistant-app"

# Test endpoints
curl https://your-service-url/health
```

## Rollback Strategy

```bash
# List revisions
gcloud run revisions list --service=the-assistant-app --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic the-assistant-app --to-revisions=REVISION_NAME=100 --region=us-central1
```